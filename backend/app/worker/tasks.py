import asyncio
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete, func, select, update
from sqlalchemy.orm import selectinload

from app.database import async_session
from app.models import FolderPath, MediaFile, ScanJob, ScanQueueItem, ScannedFolder
from app.services.scanner import scan_file, find_video_files
from app.worker.scheduler import clear_abort, get_abort_event, get_scan_lock

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def _get_mtime(path: str) -> datetime:
    return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)


def _relative_path(file_path: str, folder_path: str) -> str:
    return os.path.relpath(file_path, folder_path)


async def rebuild_folder_paths(folder_id: int, db=None):
    """Rebuild the folder_paths table for a given folder from current media_files."""
    from collections import defaultdict

    async def _do(session):
        result = await session.execute(
            select(MediaFile.relative_path)
            .where(MediaFile.folder_id == folder_id)
            .where(MediaFile.relative_path.isnot(None))
        )
        paths = [r[0] for r in result.all()]

        counts: dict[str, int] = defaultdict(int)
        for p in paths:
            parts = p.split("/")
            for i in range(1, len(parts)):
                counts["/".join(parts[:i])] += 1

        await session.execute(
            sa_delete(FolderPath).where(FolderPath.folder_id == folder_id)
        )

        if counts:
            session.add_all([
                FolderPath(folder_id=folder_id, path=path, file_count=count)
                for path, count in counts.items()
            ])
        await session.flush()

    if db:
        await _do(db)
    else:
        async with async_session() as session:
            await _do(session)
            await session.commit()


async def recover_interrupted_queue():
    """Reset any 'processing' items back to 'pending' on startup and resume processing."""
    async with async_session() as db:
        await db.execute(
            update(ScanQueueItem)
            .where(ScanQueueItem.status == "processing")
            .values(status="pending", started_at=None)
        )

        # Mark interrupted jobs as failed
        await db.execute(
            update(ScanJob)
            .where(ScanJob.status == "running")
            .values(status="failed", finished_at=func.now())
        )

        # Sync file_count for all folders based on actual media files
        folders = (await db.execute(select(ScannedFolder))).scalars().all()
        for folder in folders:
            count = await db.scalar(
                select(func.count()).select_from(MediaFile)
                .where(MediaFile.folder_id == folder.id)
            )
            folder.file_count = count or 0

        await db.commit()

        # Find folders with pending queue items to resume
        result = await db.execute(
            select(ScanQueueItem.folder_id)
            .where(ScanQueueItem.status == "pending")
            .distinct()
        )
        pending_folder_ids = [r[0] for r in result.all()]

    if pending_folder_ids:
        logger.info("Resuming queue processing for %d folder(s)", len(pending_folder_ids))
        for folder_id in pending_folder_ids:
            task = asyncio.create_task(process_queue(folder_id))
            task.add_done_callback(_log_task_exception)
    else:
        logger.info("No interrupted queue items to resume")


def _log_task_exception(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        logger.error("Background queue task failed: %s", task.exception())


async def enqueue_folder(folder_id: int, force: bool = False):
    """Discover files and add them to the scan queue."""
    async with async_session() as db:
        folder = await db.get(ScannedFolder, folder_id)
        if not folder:
            return 0

        video_files = await asyncio.to_thread(find_video_files, folder.path)

        # Find files already in queue (pending/processing) - skip these
        existing_queue = set()
        result = await db.execute(
            select(ScanQueueItem.file_path).where(
                ScanQueueItem.folder_id == folder_id,
                ScanQueueItem.status.in_(["pending", "processing"]),
            )
        )
        existing_queue = {r[0] for r in result.all()}

        # Remove failed items so they can be re-enqueued
        await db.execute(
            sa_delete(ScanQueueItem).where(
                ScanQueueItem.folder_id == folder_id,
                ScanQueueItem.status == "failed",
            )
        )
        await db.commit()

        existing_media = {}
        result = await db.execute(
            select(MediaFile.file_path, MediaFile.file_modified_at)
            .where(MediaFile.folder_id == folder_id)
        )
        existing_media = {r[0]: r[1] for r in result.all()}

        # Remove DB entries for files no longer on disk
        video_files_set = set(video_files)
        removed_paths = [p for p in existing_media if p not in video_files_set]
        if removed_paths:
            for batch_start in range(0, len(removed_paths), BATCH_SIZE):
                batch = removed_paths[batch_start:batch_start + BATCH_SIZE]
                stale = await db.execute(
                    select(MediaFile).where(MediaFile.file_path.in_(batch))
                )
                for mf in stale.scalars().all():
                    logger.info("File removed from disk, deleting from DB: %s", mf.file_path)
                    await db.delete(mf)
                await db.commit()
            logger.info("Removed %d stale file(s) from folder %s", len(removed_paths), folder.path)

        items_to_add = []
        for file_path in video_files:
            if file_path in existing_queue:
                continue

            # Skip if already scanned and mtime hasn't changed (unless force)
            if not force and file_path in existing_media:
                try:
                    mtime = await asyncio.to_thread(_get_mtime, file_path)
                    if existing_media[file_path] == mtime:
                        continue
                except OSError:
                    continue

            rel_path = _relative_path(file_path, folder.path)
            items_to_add.append(ScanQueueItem(
                folder_id=folder_id,
                file_path=file_path,
                relative_path=rel_path,
                status="pending",
            ))

            if len(items_to_add) >= BATCH_SIZE:
                db.add_all(items_to_add)
                await db.commit()
                items_to_add = []

        if items_to_add:
            db.add_all(items_to_add)
            await db.commit()

        total = await db.scalar(
            select(func.count()).select_from(ScanQueueItem)
            .where(ScanQueueItem.folder_id == folder_id)
            .where(ScanQueueItem.status == "pending")
        )
        logger.info("Enqueued %d new files for folder %s", total, folder.path)
        return total or 0, removed_paths


async def process_queue(folder_id: int):
    """Process queued items for a folder, highest priority first. Creates its own job."""
    lock = get_scan_lock(folder_id)
    if lock.locked():
        return

    async with lock:
        clear_abort(folder_id)
        async with async_session() as db:
            folder = await db.get(ScannedFolder, folder_id)
            if not folder or not folder.enabled:
                return

            job = ScanJob(folder_id=folder_id, status="running", phase="scanning")
            db.add(job)
            await db.commit()
            job_id = job.id

        await _do_process_queue(folder_id, job_id)


async def _process_queue_with_job(folder_id: int, job_id: int):
    """Process queue using an existing job (already holds the lock)."""
    await _do_process_queue(folder_id, job_id)


async def _do_process_queue(folder_id: int, job_id: int):
    """Core queue processing logic."""
    async with async_session() as db:
        job = await db.get(ScanJob, job_id)
        job.phase = "scanning"

        await db.execute(
            update(ScanQueueItem)
            .where(ScanQueueItem.folder_id == folder_id)
            .where(ScanQueueItem.status == "processing")
            .values(status="pending")
        )

        pending_count = await db.scalar(
            select(func.count()).select_from(ScanQueueItem)
            .where(ScanQueueItem.folder_id == folder_id)
            .where(ScanQueueItem.status == "pending")
        )
        job.files_found = pending_count or 0
        await db.commit()

        folder = await db.get(ScannedFolder, folder_id)

        abort_event = get_abort_event(folder_id)

        try:
            while True:
                if abort_event.is_set():
                    await db.execute(
                        update(ScanJob)
                        .where(ScanJob.id == job_id)
                        .values(status="aborted", finished_at=datetime.now(timezone.utc))
                    )
                    await db.commit()
                    logger.info("Scan aborted for folder_id=%d", folder_id)
                    return

                result = await db.execute(
                    select(ScanQueueItem)
                    .where(ScanQueueItem.folder_id == folder_id)
                    .where(ScanQueueItem.status == "pending")
                    .order_by(ScanQueueItem.priority.desc(), ScanQueueItem.id.asc())
                    .limit(1)
                )
                item = result.scalar_one_or_none()
                if not item:
                    break

                item.status = "processing"
                item.started_at = datetime.now(timezone.utc)
                await db.commit()

                try:
                    if not os.path.exists(item.file_path):
                        existing = await db.execute(
                            select(MediaFile).where(MediaFile.file_path == item.file_path)
                        )
                        existing_file = existing.scalar_one_or_none()
                        if existing_file:
                            await db.delete(existing_file)
                            job.files_removed += 1
                            if job.removed_file_paths is None:
                                job.removed_file_paths = []
                            job.removed_file_paths = job.removed_file_paths + [os.path.basename(item.file_path)]
                            logger.info("File removed from disk, deleting from DB: %s", item.file_path)
                        item.status = "completed"
                        item.completed_at = datetime.now(timezone.utc)
                        job.files_scanned += 1
                        await db.commit()
                        continue

                    mtime = await asyncio.to_thread(_get_mtime, item.file_path)

                    if item.media_file_id:
                        existing = await db.execute(
                            select(MediaFile)
                            .where(MediaFile.id == item.media_file_id)
                            .options(
                                selectinload(MediaFile.video_tracks),
                                selectinload(MediaFile.audio_tracks),
                                selectinload(MediaFile.subtitle_tracks),
                            )
                        )
                    else:
                        existing = await db.execute(
                            select(MediaFile)
                            .where(MediaFile.file_path == item.file_path)
                            .options(
                                selectinload(MediaFile.video_tracks),
                                selectinload(MediaFile.audio_tracks),
                                selectinload(MediaFile.subtitle_tracks),
                            )
                        )
                    existing_file = existing.scalar_one_or_none()

                    if item.priority < 10 and existing_file and existing_file.file_modified_at == mtime:
                        item.status = "completed"
                        item.completed_at = datetime.now(timezone.utc)
                        job.files_scanned += 1
                        await db.commit()
                        continue

                    scanned = await asyncio.to_thread(scan_file, item.file_path)
                    if scanned is None:
                        item.status = "failed"
                        item.error_message = "Parse returned None"
                        item.completed_at = datetime.now(timezone.utc)
                        job.files_scanned += 1
                        await db.commit()
                        continue

                    if existing_file:
                        existing_file.file_name = scanned.file_name
                        existing_file.file_size_bytes = scanned.file_size_bytes
                        existing_file.container_format = scanned.container_format
                        existing_file.title = scanned.title
                        existing_file.overall_bitrate = scanned.overall_bitrate
                        existing_file.duration_ms = scanned.duration_ms
                        existing_file.release_group = scanned.release_group
                        existing_file.source = scanned.source
                        existing_file.provider = scanned.provider
                        existing_file.year = scanned.year or existing_file.year
                        existing_file.stream_count = scanned.stream_count
                        existing_file.hybrid = scanned.hybrid
                        existing_file.file_modified_at = mtime
                        existing_file.relative_path = item.relative_path
                        existing_file.scanned_at = func.now()

                        existing_file.video_tracks.clear()
                        existing_file.audio_tracks.clear()
                        existing_file.subtitle_tracks.clear()
                        await db.flush()

                        new_video = list(scanned.video_tracks)
                        new_audio = list(scanned.audio_tracks)
                        new_subs = list(scanned.subtitle_tracks)
                        scanned.video_tracks.clear()
                        scanned.audio_tracks.clear()
                        scanned.subtitle_tracks.clear()

                        for vt in new_video:
                            vt.media_file_id = existing_file.id
                            vt.media_file = None
                            existing_file.video_tracks.append(vt)
                        for at in new_audio:
                            at.media_file_id = existing_file.id
                            at.media_file = None
                            existing_file.audio_tracks.append(at)
                        for st in new_subs:
                            st.media_file_id = existing_file.id
                            st.media_file = None
                            existing_file.subtitle_tracks.append(st)
                        job.files_rescanned += 1
                        if job.rescanned_file_paths is None:
                            job.rescanned_file_paths = []
                        job.rescanned_file_paths = job.rescanned_file_paths + [os.path.basename(item.file_path)]
                    else:
                        scanned.folder_id = folder_id
                        scanned.file_modified_at = mtime
                        scanned.relative_path = item.relative_path
                        db.add(scanned)

                    item.status = "completed"
                    item.completed_at = datetime.now(timezone.utc)
                    job.files_scanned += 1
                    await db.commit()
                    logger.info("Scanned: %s", item.file_path)

                except Exception as e:
                    item.status = "failed"
                    item.error_message = str(e)[:500]
                    item.completed_at = datetime.now(timezone.utc)
                    job.files_scanned += 1
                    await db.commit()
                    logger.warning("Failed to scan %s: %s", item.file_path, e)

            folder.last_scanned = datetime.now(timezone.utc)
            count = await db.scalar(
                select(func.count()).select_from(MediaFile)
                .where(MediaFile.folder_id == folder_id)
            )
            folder.file_count = count or 0
            job.status = "completed"
            job.finished_at = datetime.now(timezone.utc)
            await rebuild_folder_paths(folder_id, db)
            logger.info("Queue processing complete for folder %s: %d files", folder.path, folder.file_count)

        except Exception as e:
            logger.exception("Queue processing failed for folder_id=%d", folder_id)
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)

        await db.commit()


async def run_folder_scan(folder_id: int, force: bool = False):
    """Enqueue files then process the queue."""
    lock = get_scan_lock(folder_id)
    if lock.locked():
        return

    async with lock:
        clear_abort(folder_id)
        async with async_session() as db:
            folder = await db.get(ScannedFolder, folder_id)
            if not folder or not folder.enabled:
                return

            job = ScanJob(folder_id=folder_id, status="running", phase="discovering")
            db.add(job)
            await db.commit()
            job_id = job.id

        try:
            _enqueued, removed_paths = await enqueue_folder(folder_id, force=force)
        except Exception as e:
            async with async_session() as db:
                job = await db.get(ScanJob, job_id)
                job.status = "failed"
                job.error_message = str(e)[:500]
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
            return

        if get_abort_event(folder_id).is_set():
            async with async_session() as db:
                job = await db.get(ScanJob, job_id)
                job.status = "aborted"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
            logger.info("Scan aborted during discovery for folder_id=%d", folder_id)
            return

        if removed_paths:
            async with async_session() as db:
                job = await db.get(ScanJob, job_id)
                job.files_removed = len(removed_paths)
                job.removed_file_paths = [os.path.basename(p) for p in removed_paths]
                await db.commit()

        await _process_queue_with_job(folder_id, job_id)
