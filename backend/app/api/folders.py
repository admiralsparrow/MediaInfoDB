import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Library, ScannedFolder
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate
from app.services.folder_browser import folder_browser
from app.worker.scheduler import remove_folder_schedule, schedule_folder_scan
from app.worker.tasks import run_folder_scan

logger = logging.getLogger(__name__)


def _log_task_exception(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        logger.error("Background scan task failed: %s", task.exception())

router = APIRouter()


@router.get("", response_model=list[FolderResponse])
async def list_folders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScannedFolder)
        .options(selectinload(ScannedFolder.libraries))
        .order_by(ScannedFolder.added_at.desc())
    )
    folders = result.scalars().all()
    return [FolderResponse.from_folder(f) for f in folders]


@router.post("", response_model=FolderResponse, status_code=201)
async def add_folder(body: FolderCreate, db: AsyncSession = Depends(get_db)):
    if not folder_browser.is_path_allowed(body.path):
        raise HTTPException(status_code=403, detail="Path outside allowed roots")

    existing = await db.execute(
        select(ScannedFolder).where(ScannedFolder.path == body.path)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Folder already added")

    # Validate libraries exist
    libs_result = await db.execute(
        select(Library).where(Library.id.in_(body.library_ids))
    )
    libraries = libs_result.scalars().all()
    if len(libraries) != len(body.library_ids):
        raise HTTPException(status_code=400, detail="One or more library IDs not found")

    folder = ScannedFolder(path=body.path, scan_interval_minutes=body.scan_interval_minutes)
    folder.libraries = list(libraries)
    db.add(folder)
    await db.commit()
    await db.refresh(folder, ["libraries"])

    schedule_folder_scan(folder.id, folder.scan_interval_minutes)
    task = asyncio.create_task(run_folder_scan(folder.id))
    task.add_done_callback(_log_task_exception)

    return FolderResponse.from_folder(folder)


@router.delete("/{folder_id}", status_code=204)
async def remove_folder(folder_id: int, db: AsyncSession = Depends(get_db)):
    folder = await db.get(ScannedFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    remove_folder_schedule(folder_id)
    await db.delete(folder)
    await db.commit()


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(folder_id: int, body: FolderUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScannedFolder)
        .options(selectinload(ScannedFolder.libraries))
        .where(ScannedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    if body.enabled is not None:
        folder.enabled = body.enabled
    if body.library_ids is not None:
        libs_result = await db.execute(
            select(Library).where(Library.id.in_(body.library_ids))
        )
        folder.libraries = list(libs_result.scalars().all())
    if body.scan_interval_minutes is not None:
        folder.scan_interval_minutes = body.scan_interval_minutes
        schedule_folder_scan(folder_id, body.scan_interval_minutes)

    await db.commit()
    await db.refresh(folder, ["libraries"])
    return FolderResponse.from_folder(folder)


@router.delete("/{folder_id}/library/{library_id}", status_code=204)
async def remove_folder_from_library(
    folder_id: int, library_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(ScannedFolder)
        .options(selectinload(ScannedFolder.libraries))
        .where(ScannedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    folder.libraries = [lib for lib in folder.libraries if lib.id != library_id]

    if not folder.libraries:
        remove_folder_schedule(folder_id)
        await db.delete(folder)
    await db.commit()


@router.post("/{folder_id}/rescan", status_code=202)
async def rescan_folder(
    folder_id: int,
    force: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    folder = await db.get(ScannedFolder, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    task = asyncio.create_task(run_folder_scan(folder_id, force=force))
    task.add_done_callback(_log_task_exception)
    return {"message": "Scan triggered"}
