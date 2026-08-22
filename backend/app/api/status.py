from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import ScanJob, ScannedFolder
from app.worker.scheduler import request_abort

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


@router.post("/scans/{job_id}/abort")
async def abort_scan(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(ScanJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    if job.status != "running":
        raise HTTPException(status_code=409, detail="Scan is not running")

    request_abort(job.folder_id)

    await db.execute(
        update(ScanJob)
        .where(ScanJob.id == job_id)
        .values(status="aborted", finished_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return {"message": "Abort requested"}
