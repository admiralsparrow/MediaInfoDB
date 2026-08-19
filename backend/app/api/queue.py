from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ScanQueueItem, ScannedFolder

router = APIRouter()


class QueueItemResponse(BaseModel):
    id: int
    folder_id: int
    file_path: str
    relative_path: str
    priority: int
    status: str
    error_message: str | None

    class Config:
        from_attributes = True


class QueueSummaryResponse(BaseModel):
    folder_id: int
    folder_path: str
    pending: int
    processing: int
    completed: int
    failed: int


class PriorityUpdate(BaseModel):
    priority: int


class BulkPriorityUpdate(BaseModel):
    prefix: str
    folder_id: int
    priority: int


@router.get("", response_model=list[QueueItemResponse])
async def list_queue(
    folder_id: int | None = None,
    status: str = "pending",
    limit: int = Query(default=100, le=1000),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(ScanQueueItem).where(ScanQueueItem.status == status)
    if folder_id:
        query = query.where(ScanQueueItem.folder_id == folder_id)
    query = query.order_by(ScanQueueItem.priority.desc(), ScanQueueItem.id.asc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/summary", response_model=list[QueueSummaryResponse])
async def queue_summary(
    folder_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(
            ScanQueueItem.folder_id,
            ScanQueueItem.status,
            func.count().label("count"),
        )
        .group_by(ScanQueueItem.folder_id, ScanQueueItem.status)
    )
    if folder_id:
        query = query.where(ScanQueueItem.folder_id == folder_id)

    result = await db.execute(query)
    rows = result.all()

    # Group by folder
    folders: dict[int, dict] = {}
    for fid, status, count in rows:
        if fid not in folders:
            folders[fid] = {"folder_id": fid, "folder_path": "", "pending": 0, "processing": 0, "completed": 0, "failed": 0}
        folders[fid][status] = count

    # Fetch folder paths
    if folders:
        path_result = await db.execute(
            select(ScannedFolder.id, ScannedFolder.path).where(ScannedFolder.id.in_(folders.keys()))
        )
        for fid, path in path_result.all():
            folders[fid]["folder_path"] = path

    return list(folders.values())


@router.get("/subfolders")
async def queue_subfolders(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get subfolder tree with pending counts for prioritization UI."""
    result = await db.execute(
        select(ScanQueueItem.relative_path)
        .where(ScanQueueItem.folder_id == folder_id)
        .where(ScanQueueItem.status == "pending")
    )
    paths = [r[0] for r in result.all()]

    # Count files per top-level subfolder
    subfolder_counts: dict[str, int] = {}
    for p in paths:
        parts = p.split("/")
        top = parts[0] if len(parts) > 1 else "."
        subfolder_counts[top] = subfolder_counts.get(top, 0) + 1

    return sorted(
        [{"subfolder": k, "pending_count": v} for k, v in subfolder_counts.items()],
        key=lambda x: x["pending_count"],
        reverse=True,
    )


@router.patch("/{item_id}/priority")
async def set_item_priority(
    item_id: int,
    body: PriorityUpdate,
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ScanQueueItem, item_id)
    if not item:
        raise HTTPException(status_code=404)
    item.priority = body.priority
    await db.commit()
    return {"ok": True}


@router.post("/prioritize-subfolder")
async def prioritize_subfolder(
    body: BulkPriorityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Bump all pending items in a subfolder to the given priority."""
    prefix = body.prefix.rstrip("/") + "/"
    result = await db.execute(
        update(ScanQueueItem)
        .where(ScanQueueItem.folder_id == body.folder_id)
        .where(ScanQueueItem.status == "pending")
        .where(ScanQueueItem.relative_path.like(prefix + "%"))
        .values(priority=body.priority)
    )
    await db.commit()
    return {"updated": result.rowcount}


@router.delete("/completed")
async def clear_completed(
    folder_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Remove completed items from the queue."""
    from sqlalchemy import delete as sa_delete

    query = sa_delete(ScanQueueItem).where(ScanQueueItem.status == "completed")
    if folder_id:
        query = query.where(ScanQueueItem.folder_id == folder_id)
    result = await db.execute(query)
    await db.commit()
    return {"deleted": result.rowcount}


@router.delete("/failed")
async def clear_failed(
    folder_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Remove failed items from the queue so they can be retried on next scan."""
    from sqlalchemy import delete as sa_delete

    query = sa_delete(ScanQueueItem).where(ScanQueueItem.status == "failed")
    if folder_id:
        query = query.where(ScanQueueItem.folder_id == folder_id)
    result = await db.execute(query)
    await db.commit()
    return {"deleted": result.rowcount}
