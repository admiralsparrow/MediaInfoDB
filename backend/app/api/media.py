import asyncio
import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import AudioTrack, MediaFile, VideoTrack
from app.models.scan_queue import ScanQueueItem
from app.schemas.media_file import MediaFileDetailResponse, MediaFileResponse
from app.services.filter_builder import FILTER_REGISTRY, build_media_query, get_filter_options
from app.worker.tasks import process_queue

logger = logging.getLogger(__name__)


def _log_task_exception(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        logger.error("Background task failed: %s", task.exception())

SORT_MAP = {
    "file_name": MediaFile.file_name,
    "title": MediaFile.title,
    "container_format": MediaFile.container_format,
    "overall_bitrate": MediaFile.overall_bitrate,
    "duration_ms": MediaFile.duration_ms,
    "file_size_bytes": MediaFile.file_size_bytes,
    "relative_path": MediaFile.relative_path,
    "release_group": MediaFile.release_group,
    "source": MediaFile.source,
    "provider": MediaFile.provider,
    "scanned_at": MediaFile.scanned_at,
    "file_modified_at": MediaFile.file_modified_at,
    "video_codec": (VideoTrack, "codec"),
    "video_bitrate": (VideoTrack, "bitrate"),
    "video_width": (VideoTrack, "width"),
    "video_height": (VideoTrack, "height"),
    "video_framerate": (VideoTrack, "framerate"),
    "audio_codec": (AudioTrack, "codec"),
    "audio_bitrate": (AudioTrack, "bitrate"),
    "audio_channels": (AudioTrack, "channels"),
    "audio_sample_rate": (AudioTrack, "sample_rate"),
    "year": MediaFile.year,
    "stream_count": MediaFile.stream_count,
    "hybrid": MediaFile.hybrid,
    "video_bit_depth": (VideoTrack, "bit_depth"),
    "video_aspect_ratio": (VideoTrack, "display_aspect_ratio"),
    "video_resolution": (VideoTrack, "resolution"),
}

router = APIRouter()


@router.get("", response_model=list[MediaFileDetailResponse])
async def list_media(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="file_name"),
    order: str = Query(default="asc"),
    db: AsyncSession = Depends(get_db),
):
    if sort not in SORT_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort}")
    if order not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")

    recognized_keys = set(FILTER_REGISTRY.keys()) | {"library_id", "folder_id"}
    filters = {k: v for k, v in request.query_params.items() if k in recognized_keys}

    sort_spec = SORT_MAP[sort]
    offset = (page - 1) * page_size

    if isinstance(sort_spec, tuple):
        model, col_name = sort_spec
        sort_col = getattr(model, col_name)
        sort_agg = func.min(sort_col)
        base_subq = build_media_query(filters).subquery()
        id_query = (
            select(base_subq.c.id)
            .outerjoin(model, model.media_file_id == base_subq.c.id)
            .group_by(base_subq.c.id)
        )
        if order == "desc":
            id_query = id_query.order_by(func.max(sort_col).desc().nulls_last())
        else:
            id_query = id_query.order_by(sort_agg.asc().nulls_last())
        id_query = id_query.offset(offset).limit(page_size)
        id_result = await db.execute(id_query)
        ids = [row[0] for row in id_result.all()]
        if not ids:
            return []
        query = (
            select(MediaFile)
            .where(MediaFile.id.in_(ids))
            .options(
                selectinload(MediaFile.video_tracks),
                selectinload(MediaFile.audio_tracks),
                selectinload(MediaFile.subtitle_tracks),
            )
        )
        result = await db.execute(query)
        files_map = {f.id: f for f in result.scalars().all()}
        return [files_map[i] for i in ids if i in files_map]
    else:
        query = build_media_query(filters)
        if order == "desc":
            query = query.order_by(sort_spec.desc())
        else:
            query = query.order_by(sort_spec.asc())
        query = query.offset(offset).limit(page_size)
        query = query.options(
            selectinload(MediaFile.video_tracks),
            selectinload(MediaFile.audio_tracks),
            selectinload(MediaFile.subtitle_tracks),
        )
        result = await db.execute(query)
        return result.scalars().all()


@router.get("/count")
async def media_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    recognized_keys = set(FILTER_REGISTRY.keys()) | {"library_id", "folder_id"}
    filters = {k: v for k, v in request.query_params.items() if k in recognized_keys}
    query = build_media_query(filters)
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    return {"count": result.scalar()}


@router.get("/filters/options")
async def filter_options(
    library_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_filter_options(db, library_id=library_id)


@router.get("/folders/tree")
async def folder_tree(
    library_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get distinct subfolder paths for the folder filter tree."""
    from app.models import ScannedFolder
    from app.models.library import library_folders as lf

    query = select(MediaFile.relative_path).where(
        MediaFile.relative_path.isnot(None)
    ).distinct()
    if library_id:
        query = query.join(ScannedFolder).join(lf, lf.c.folder_id == ScannedFolder.id)
        query = query.where(lf.c.library_id == library_id)

    result = await db.execute(query)
    paths = [r[0] for r in result.all()]

    dirs: set[str] = set()
    for p in paths:
        parts = p.split("/")
        for i in range(1, len(parts)):
            dirs.add("/".join(parts[:i]))

    return sorted(dirs)


@router.post("/rescan", status_code=202)
async def rescan_files(
    file_ids: list[int] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    if not file_ids:
        raise HTTPException(status_code=400, detail="No file IDs provided")
    if len(file_ids) > 5000:
        raise HTTPException(status_code=400, detail="Maximum 5000 files per request")

    result = await db.execute(
        select(MediaFile.id, MediaFile.file_path, MediaFile.relative_path, MediaFile.folder_id)
        .where(MediaFile.id.in_(file_ids))
    )
    files = result.all()
    if not files:
        raise HTTPException(status_code=404, detail="No matching files found")

    folder_ids = set()
    for f in files:
        stmt = (
            pg_insert(ScanQueueItem)
            .values(
                folder_id=f.folder_id,
                media_file_id=f.id,
                file_path=f.file_path,
                relative_path=f.relative_path,
                priority=10,
                status="pending",
            )
            .on_conflict_do_update(
                index_elements=["file_path"],
                index_where=text("status IN ('pending', 'processing')"),
                set_={"priority": 10, "media_file_id": f.id, "status": "pending"},
            )
        )
        await db.execute(stmt)
        folder_ids.add(f.folder_id)

    await db.commit()

    for fid in folder_ids:
        task = asyncio.create_task(process_queue(fid))
        task.add_done_callback(_log_task_exception)

    return {"message": f"Rescan queued for {len(files)} file(s)"}


@router.get("/{media_id}", response_model=MediaFileDetailResponse)
async def get_media_detail(media_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MediaFile)
        .where(MediaFile.id == media_id)
        .options(
            selectinload(MediaFile.video_tracks),
            selectinload(MediaFile.audio_tracks),
            selectinload(MediaFile.subtitle_tracks),
        )
    )
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media file not found")
    return media
