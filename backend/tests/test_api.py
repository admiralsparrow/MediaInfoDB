"""
API integration tests using FastAPI TestClient with an in-memory SQLite database.
Tests all endpoint routers: libraries, folders, media, queue, logs, browse, status.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.base import Base
from app.models import (
    AudioTrack,
    Library,
    MediaFile,
    ScanJob,
    ScanQueueItem,
    ScannedFolder,
    SubtitleTrack,
    VideoTrack,
    library_folders,
)
from tests.conftest import create_test_engine


@pytest_asyncio.fixture
async def db_engine():
    engine = create_test_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def app(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    test_app = FastAPI()

    from app.api.router import api_router
    test_app.include_router(api_router, prefix="/api/v1")

    from app.database import get_db
    test_app.dependency_overrides[get_db] = override_get_db

    return test_app


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_library(db_session):
    lib = Library(name="Movies")
    db_session.add(lib)
    await db_session.commit()
    await db_session.refresh(lib)
    return lib


@pytest_asyncio.fixture
async def seed_folder(db_session, seed_library):
    folder = ScannedFolder(path="/media/movies", enabled=True, file_count=0)
    db_session.add(folder)
    await db_session.flush()
    await db_session.execute(
        library_folders.insert().values(library_id=seed_library.id, folder_id=folder.id)
    )
    await db_session.commit()
    await db_session.refresh(folder)
    return folder


@pytest_asyncio.fixture
async def seed_media(db_session, seed_folder):
    mf = MediaFile(
        folder_id=seed_folder.id,
        file_path="/media/movies/Movie.2024.mkv",
        file_name="Movie.2024.mkv",
        relative_path="Movie.2024.mkv",
        file_size_bytes=1_000_000,
        container_format="Matroska",
        overall_bitrate=5_000_000,
        duration_ms=120_000,
        release_group="GROUP",
        source="WEB-DL",
        provider="NF",
        year=2024,
        hybrid=False,
        stream_count=3,
    )
    db_session.add(mf)
    await db_session.flush()

    vt = VideoTrack(
        media_file_id=mf.id, track_index=0, codec="HEVC", bitrate=4_000_000,
        width=3840, height=2160, framerate=23.976, hdr10=True, dolby_vision=False,
        hdr10_plus=False, is_default=True, is_forced=False, resolution="2160p",
    )
    at = AudioTrack(
        media_file_id=mf.id, track_index=1, codec="AAC", bitrate=128_000,
        channels=2, channel_layout="2.0", language="en", is_default=True,
        is_original=False, is_forced=False, is_commentary=False, is_atmos=False,
    )
    st = SubtitleTrack(
        media_file_id=mf.id, track_index=2, codec="SRT", language="en",
        is_default=True, is_forced=False, is_hearing_impaired=False,
    )
    db_session.add_all([vt, at, st])
    await db_session.commit()
    await db_session.refresh(mf)
    return mf


# ── Library endpoints ───────────────────────────────────────────────

class TestLibraryAPI:
    @pytest.mark.asyncio
    async def test_create_library(self, client):
        resp = await client.post("/api/v1/libraries", json={"name": "TV Shows"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "TV Shows"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_duplicate_library(self, client, seed_library):
        resp = await client.post("/api/v1/libraries", json={"name": "Movies"})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_libraries(self, client, seed_library):
        resp = await client.get("/api/v1/libraries")
        assert resp.status_code == 200
        libs = resp.json()
        assert len(libs) >= 1
        assert any(lib["name"] == "Movies" for lib in libs)

    @pytest.mark.asyncio
    async def test_update_library(self, client, seed_library):
        resp = await client.patch(f"/api/v1/libraries/{seed_library.id}", json={"name": "Films"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Films"

    @pytest.mark.asyncio
    async def test_update_nonexistent_library(self, client):
        resp = await client.patch("/api/v1/libraries/9999", json={"name": "X"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_library(self, client, seed_library):
        resp = await client.delete(f"/api/v1/libraries/{seed_library.id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_library(self, client):
        resp = await client.delete("/api/v1/libraries/9999")
        assert resp.status_code == 404


# ── Media endpoints ─────────────────────────────────────────────────

class TestMediaAPI:
    @pytest.mark.asyncio
    async def test_list_media(self, client, seed_media):
        resp = await client.get("/api/v1/media")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["file_name"] == "Movie.2024.mkv"
        assert len(data[0]["video_tracks"]) == 1
        assert len(data[0]["audio_tracks"]) == 1
        assert len(data[0]["subtitle_tracks"]) == 1

    @pytest.mark.asyncio
    async def test_list_media_with_pagination(self, client, seed_media):
        resp = await client.get("/api/v1/media?page=1&page_size=10")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_media_sorted_by_file_name(self, client, seed_media):
        resp = await client.get("/api/v1/media?sort=file_name&order=desc")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_media_sorted_by_track_field(self, client, seed_media):
        resp = await client.get("/api/v1/media?sort=video_codec&order=asc")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_media_invalid_sort(self, client, seed_media):
        resp = await client.get("/api/v1/media?sort=nonexistent")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_media_invalid_order(self, client, seed_media):
        resp = await client.get("/api/v1/media?sort=file_name&order=sideways")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_media_count(self, client, seed_media):
        resp = await client.get("/api/v1/media/count")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    @pytest.mark.asyncio
    async def test_media_count_with_filter(self, client, seed_media):
        resp = await client.get("/api/v1/media/count?source=WEB-DL")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        resp2 = await client.get("/api/v1/media/count?source=BluRay")
        assert resp2.json()["count"] == 0

    @pytest.mark.asyncio
    async def test_get_media_detail(self, client, seed_media):
        resp = await client.get(f"/api/v1/media/{seed_media.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["file_name"] == "Movie.2024.mkv"
        assert data["video_tracks"][0]["codec"] == "HEVC"
        assert data["audio_tracks"][0]["codec"] == "AAC"

    @pytest.mark.asyncio
    async def test_get_media_detail_not_found(self, client):
        resp = await client.get("/api/v1/media/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_filter_options(self, client, seed_media):
        resp = await client.get("/api/v1/media/filters/options")
        assert resp.status_code == 200
        opts = resp.json()
        assert isinstance(opts, dict)

    @pytest.mark.asyncio
    async def test_folder_children(self, client, seed_media):
        resp = await client.get("/api/v1/media/folders/children")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="pg_insert ON CONFLICT with partial index requires PostgreSQL")
    @patch("app.worker.tasks.process_queue", new_callable=AsyncMock)
    async def test_rescan_files(self, mock_process, client, seed_media):
        resp = await client.post(
            "/api/v1/media/rescan",
            json={"file_ids": [seed_media.id]},
        )
        assert resp.status_code == 202
        assert "Rescan queued" in resp.json()["message"]

    @pytest.mark.asyncio
    async def test_rescan_empty_ids(self, client):
        resp = await client.post("/api/v1/media/rescan", json={"file_ids": []})
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_rescan_nonexistent_ids(self, client):
        resp = await client.post("/api/v1/media/rescan", json={"file_ids": [9999]})
        assert resp.status_code == 404


# ── Browse endpoint ─────────────────────────────────────────────────

class TestBrowseAPI:
    @pytest.mark.asyncio
    @patch("app.api.browse.folder_browser")
    async def test_browse_roots(self, mock_browser, client):
        mock_browser.get_roots.return_value = [
            {"name": "media", "path": "/media", "has_children": True}
        ]
        resp = await client.get("/api/v1/browse")
        assert resp.status_code == 200
        assert resp.json()[0]["name"] == "media"

    @pytest.mark.asyncio
    @patch("app.api.browse.folder_browser")
    async def test_browse_directory(self, mock_browser, client):
        mock_browser.list_directory.return_value = [
            {"name": "movies", "path": "/media/movies", "has_children": True}
        ]
        resp = await client.get("/api/v1/browse?path=/media")
        assert resp.status_code == 200
        assert resp.json()[0]["name"] == "movies"

    @pytest.mark.asyncio
    @patch("app.api.browse.folder_browser")
    async def test_browse_forbidden(self, mock_browser, client):
        mock_browser.list_directory.side_effect = PermissionError("Path outside allowed roots")
        resp = await client.get("/api/v1/browse?path=/etc")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.browse.folder_browser")
    async def test_browse_not_found(self, mock_browser, client):
        mock_browser.list_directory.side_effect = FileNotFoundError("Not a directory")
        resp = await client.get("/api/v1/browse?path=/media/nonexistent")
        assert resp.status_code == 404


# ── Folder endpoints ────────────────────────────────────────────────

class TestFolderAPI:
    @pytest.mark.asyncio
    async def test_list_folders(self, client, seed_folder):
        resp = await client.get("/api/v1/folders")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    @patch("app.api.folders.folder_browser")
    @patch("app.api.folders.run_folder_scan", new_callable=AsyncMock)
    @patch("app.api.folders.schedule_folder_scan")
    async def test_add_folder(self, mock_sched, mock_scan, mock_browser, client, seed_library):
        mock_browser.is_path_allowed.return_value = True
        resp = await client.post("/api/v1/folders", json={
            "path": "/media/tv",
            "library_ids": [seed_library.id],
        })
        assert resp.status_code == 201
        assert resp.json()["path"] == "/media/tv"

    @pytest.mark.asyncio
    @patch("app.api.folders.folder_browser")
    async def test_add_folder_disallowed_path(self, mock_browser, client, seed_library):
        mock_browser.is_path_allowed.return_value = False
        resp = await client.post("/api/v1/folders", json={
            "path": "/etc/secret",
            "library_ids": [seed_library.id],
        })
        assert resp.status_code == 403

    @pytest.mark.asyncio
    @patch("app.api.folders.remove_folder_schedule")
    async def test_delete_folder(self, mock_unsched, client, seed_folder):
        resp = await client.delete(f"/api/v1/folders/{seed_folder.id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_folder(self, client):
        resp = await client.delete("/api/v1/folders/9999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    @patch("app.api.folders.run_folder_scan", new_callable=AsyncMock)
    async def test_rescan_folder(self, mock_scan, client, seed_folder):
        resp = await client.post(f"/api/v1/folders/{seed_folder.id}/rescan")
        assert resp.status_code == 202

    @pytest.mark.asyncio
    async def test_rescan_nonexistent_folder(self, client):
        resp = await client.post("/api/v1/folders/9999/rescan")
        assert resp.status_code == 404


# ── Status / Health ─────────────────────────────────────────────────

class TestStatusAPI:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_active_scans_empty(self, client):
        resp = await client.get("/api/v1/scans/active")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_abort_nonexistent_scan(self, client):
        resp = await client.post("/api/v1/scans/9999/abort")
        assert resp.status_code == 404


# ── Queue endpoints ─────────────────────────────────────────────────

class TestQueueAPI:
    @pytest.mark.asyncio
    async def test_list_queue_empty(self, client):
        resp = await client.get("/api/v1/queue")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_queue_summary_empty(self, client):
        resp = await client.get("/api/v1/queue/summary")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_clear_completed(self, client):
        resp = await client.delete("/api/v1/queue/completed")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 0

    @pytest.mark.asyncio
    async def test_clear_failed(self, client):
        resp = await client.delete("/api/v1/queue/failed")
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 0

    @pytest.mark.asyncio
    async def test_set_priority_not_found(self, client):
        resp = await client.patch("/api/v1/queue/9999/priority", json={"priority": 10})
        assert resp.status_code == 404


# ── Scan Logs ───────────────────────────────────────────────────────

class TestLogsAPI:
    @pytest.mark.asyncio
    async def test_get_logs_empty(self, client):
        resp = await client.get("/api/v1/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_get_logs_with_data(self, client, seed_folder, db_session):
        job = ScanJob(
            folder_id=seed_folder.id,
            status="completed",
            files_found=10,
            files_scanned=10,
            files_removed=0,
            files_rescanned=0,
        )
        db_session.add(job)
        await db_session.commit()

        resp = await client.get("/api/v1/logs")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_scan_job_files_not_found(self, client):
        resp = await client.get("/api/v1/logs/9999/files")
        assert resp.status_code == 404
