from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import ScanJob, ScannedFolder

router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "healthy"}


@router.get("/scans/active")
async def active_scans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScanJob)
        .options(joinedload(ScanJob.folder))
        .where(ScanJob.status == "running")
        .order_by(ScanJob.started_at.desc())
    )
    jobs = result.scalars().all()

    return [
        {
            "id": job.id,
            "folder_id": job.folder_id,
            "folder_path": job.folder.path if job.folder else "unknown",
            "phase": job.phase,
            "files_found": job.files_found,
            "files_scanned": job.files_scanned,
        }
        for job in jobs
    ]
