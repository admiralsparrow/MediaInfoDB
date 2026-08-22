import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

scheduler = AsyncIOScheduler()
_scan_locks: dict[int, asyncio.Lock] = {}
_abort_events: dict[int, asyncio.Event] = {}


def get_scan_lock(folder_id: int) -> asyncio.Lock:
    if folder_id not in _scan_locks:
        _scan_locks[folder_id] = asyncio.Lock()
    return _scan_locks[folder_id]


def get_abort_event(folder_id: int) -> asyncio.Event:
    if folder_id not in _abort_events:
        _abort_events[folder_id] = asyncio.Event()
    return _abort_events[folder_id]


def request_abort(folder_id: int):
    get_abort_event(folder_id).set()


def clear_abort(folder_id: int):
    get_abort_event(folder_id).clear()


async def start_scheduler():
    from app.database import async_session
    from app.models import ScannedFolder
    from sqlalchemy import select

    scheduler.start()

    async with async_session() as db:
        result = await db.execute(
            select(ScannedFolder).where(ScannedFolder.enabled == True)
        )
        folders = result.scalars().all()
        for folder in folders:
            schedule_folder_scan(folder.id, folder.scan_interval_minutes)


async def shutdown_scheduler():
    scheduler.shutdown(wait=False)


def schedule_folder_scan(folder_id: int, interval_minutes: int | None = None):
    interval = interval_minutes or settings.SCAN_INTERVAL_MINUTES
    if interval <= 0:
        remove_folder_schedule(folder_id)
        return
    from app.worker.tasks import run_folder_scan

    scheduler.add_job(
        run_folder_scan,
        trigger=IntervalTrigger(minutes=interval),
        id=f"scan_folder_{folder_id}",
        args=[folder_id],
        replace_existing=True,
    )


def remove_folder_schedule(folder_id: int):
    job_id = f"scan_folder_{folder_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
