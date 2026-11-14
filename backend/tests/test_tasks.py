"""Tests for worker/tasks.py helper functions and rebuild_folder_paths."""

import os
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import FolderPath, MediaFile, ScanJob, ScanQueueItem, ScannedFolder
from app.models.base import Base
from app.worker.tasks import _get_mtime, _relative_path, rebuild_folder_paths
from tests.conftest import create_test_engine


class TestHelpers:
    def test_relative_path(self):
        assert _relative_path("/media/movies/subdir/file.mkv", "/media/movies") == "subdir/file.mkv"

    def test_relative_path_same_dir(self):
        assert _relative_path("/media/movies/file.mkv", "/media/movies") == "file.mkv"

    def test_get_mtime(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        mtime = _get_mtime(str(f))
        assert isinstance(mtime, datetime)
        assert mtime.tzinfo == timezone.utc

    def test_get_mtime_is_recent(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        mtime = _get_mtime(str(f))
        now = datetime.now(tz=timezone.utc)
        assert (now - mtime).total_seconds() < 5


@pytest_asyncio.fixture
async def db():
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


class TestRebuildFolderPaths:
    @pytest.mark.asyncio
    async def test_builds_paths_from_media_files(self, db):
        folder = ScannedFolder(path="/media/movies", enabled=True, file_count=0)
        db.add(folder)
        await db.flush()

        mf1 = MediaFile(
            folder_id=folder.id, file_path="/media/movies/a/b/file1.mkv",
            file_name="file1.mkv", relative_path="a/b/file1.mkv",
        )
        mf2 = MediaFile(
            folder_id=folder.id, file_path="/media/movies/a/file2.mkv",
            file_name="file2.mkv", relative_path="a/file2.mkv",
        )
        mf3 = MediaFile(
            folder_id=folder.id, file_path="/media/movies/a/b/file3.mkv",
            file_name="file3.mkv", relative_path="a/b/file3.mkv",
        )
        db.add_all([mf1, mf2, mf3])
        await db.commit()

        await rebuild_folder_paths(folder.id, db)

        result = await db.execute(
            select(FolderPath).where(FolderPath.folder_id == folder.id)
        )
        paths = {fp.path: fp.file_count for fp in result.scalars().all()}

        assert paths["a"] == 3
        assert paths["a/b"] == 2

    @pytest.mark.asyncio
    async def test_empty_folder(self, db):
        folder = ScannedFolder(path="/media/empty", enabled=True, file_count=0)
        db.add(folder)
        await db.commit()

        await rebuild_folder_paths(folder.id, db)

        result = await db.execute(
            select(FolderPath).where(FolderPath.folder_id == folder.id)
        )
        assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_replaces_existing_paths(self, db):
        folder = ScannedFolder(path="/media/movies", enabled=True, file_count=0)
        db.add(folder)
        await db.flush()

        db.add(FolderPath(folder_id=folder.id, path="old", file_count=99))
        mf = MediaFile(
            folder_id=folder.id, file_path="/media/movies/new/file.mkv",
            file_name="file.mkv", relative_path="new/file.mkv",
        )
        db.add(mf)
        await db.commit()

        await rebuild_folder_paths(folder.id, db)

        result = await db.execute(
            select(FolderPath).where(FolderPath.folder_id == folder.id)
        )
        paths = [fp.path for fp in result.scalars().all()]
        assert "old" not in paths
        assert "new" in paths

    @pytest.mark.asyncio
    async def test_root_files_no_paths(self, db):
        folder = ScannedFolder(path="/media/movies", enabled=True, file_count=0)
        db.add(folder)
        await db.flush()

        mf = MediaFile(
            folder_id=folder.id, file_path="/media/movies/file.mkv",
            file_name="file.mkv", relative_path="file.mkv",
        )
        db.add(mf)
        await db.commit()

        await rebuild_folder_paths(folder.id, db)

        result = await db.execute(
            select(FolderPath).where(FolderPath.folder_id == folder.id)
        )
        assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_null_relative_path_ignored(self, db):
        folder = ScannedFolder(path="/media/movies", enabled=True, file_count=0)
        db.add(folder)
        await db.flush()

        mf = MediaFile(
            folder_id=folder.id, file_path="/media/movies/file.mkv",
            file_name="file.mkv", relative_path=None,
        )
        db.add(mf)
        await db.commit()

        await rebuild_folder_paths(folder.id, db)

        result = await db.execute(
            select(FolderPath).where(FolderPath.folder_id == folder.id)
        )
        assert result.scalars().all() == []
