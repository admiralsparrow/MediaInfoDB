from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import ScanJob, ScannedFolder
from app.models.media_file import MediaFile

router = APIRouter()


@router.get("")
async def get_scan_logs(
    db: AsyncSession = Depends(get_db),
    folder_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = select(ScanJob).options(joinedload(ScanJob.folder))

    if folder_id is not None:
        query = query.where(ScanJob.folder_id == folder_id)
    if status is not None:
        query = query.where(ScanJob.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(ScanJob.started_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": job.id,
                "folder_id": job.folder_id,
                "folder_path": job.folder.path if job.folder else "unknown",
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                "status": job.status,
                "files_found": job.files_found,
                "files_scanned": job.files_scanned,
                "error_message": job.error_message,
            }
            for job in jobs
        ],
    }


@router.get("/{job_id}/files")
async def get_scan_job_files(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(ScanJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")

    query = (
        select(MediaFile.id, MediaFile.file_name, MediaFile.relative_path, MediaFile.scanned_at)
        .where(MediaFile.folder_id == job.folder_id)
        .where(MediaFile.scanned_at >= job.started_at)
    )
    if job.finished_at:
        query = query.where(MediaFile.scanned_at <= job.finished_at)

    query = query.order_by(MediaFile.relative_path)
    result = await db.execute(query)
    rows = result.all()

    return {
        "files": [
            {
                "id": row.id,
                "file_name": row.file_name,
                "relative_path": row.relative_path or row.file_name,
            }
            for row in rows
        ],
    }
