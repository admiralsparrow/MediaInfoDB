from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.folder import FolderCreate, FolderUpdate
from app.schemas.library import LibraryCreate, LibraryDetailResponse, LibraryResponse, LibraryUpdate
from app.schemas.media_file import (
    AudioTrackResponse,
    MediaFileDetailResponse,
    MediaFileResponse,
    SubtitleTrackResponse,
    VideoTrackResponse,
)


class TestFolderCreate:
    def test_valid(self):
        fc = FolderCreate(path="/media/movies", library_ids=[1])
        assert fc.path == "/media/movies"
        assert fc.library_ids == [1]

    def test_multiple_libraries(self):
        fc = FolderCreate(path="/media/movies", library_ids=[1, 2, 3])
        assert len(fc.library_ids) == 3

    def test_empty_library_ids_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            FolderCreate(path="/media/movies", library_ids=[])
        assert "at least one library" in str(exc_info.value).lower()

    def test_optional_scan_interval(self):
        fc = FolderCreate(path="/media", library_ids=[1], scan_interval_minutes=120)
        assert fc.scan_interval_minutes == 120

        fc2 = FolderCreate(path="/media", library_ids=[1])
        assert fc2.scan_interval_minutes is None


class TestFolderUpdate:
    def test_all_none_is_valid(self):
        fu = FolderUpdate()
        assert fu.enabled is None
        assert fu.scan_interval_minutes is None
        assert fu.library_ids is None

    def test_partial_update(self):
        fu = FolderUpdate(enabled=False)
        assert fu.enabled is False
        assert fu.scan_interval_minutes is None


class TestLibrarySchemas:
    def test_create(self):
        lc = LibraryCreate(name="Movies")
        assert lc.name == "Movies"

    def test_update(self):
        lu = LibraryUpdate(name="TV Shows")
        assert lu.name == "TV Shows"

    def test_update_empty(self):
        lu = LibraryUpdate()
        assert lu.name is None


class TestMediaFileResponse:
    def test_minimal(self):
        data = {
            "id": 1,
            "file_path": "/media/movie.mkv",
            "file_name": "movie.mkv",
            "relative_path": None,
            "file_size_bytes": None,
            "container_format": None,
            "title": None,
            "overall_bitrate": None,
            "duration_ms": None,
            "release_group": None,
            "source": None,
            "provider": None,
            "year": None,
            "stream_count": None,
            "hybrid": False,
            "scanned_at": datetime.now(),
            "file_modified_at": None,
        }
        resp = MediaFileResponse(**data)
        assert resp.file_name == "movie.mkv"
        assert resp.hybrid is False


class TestVideoTrackResponse:
    def test_from_dict(self):
        data = {
            "id": 1,
            "track_index": 0,
            "codec": "HEVC",
            "bitrate": 5000000,
            "width": 3840,
            "height": 2160,
            "framerate": 23.976,
            "hdr10": True,
            "dolby_vision": True,
            "dv_layer": "6",
            "dv_profile": 8,
            "hdr10_plus": False,
            "language": "en",
            "track_name": None,
            "is_default": True,
            "is_forced": False,
            "display_aspect_ratio": "1.78:1",
            "bit_depth": 10,
            "color_primaries": "BT.2020",
            "transfer_characteristics": "PQ",
            "encoding_library": "x265",
            "scan_type": "Progressive",
            "chroma_subsampling": "4:2:0",
            "resolution": "2160p",
        }
        resp = VideoTrackResponse(**data)
        assert resp.codec == "HEVC"
        assert resp.hdr10 is True
        assert resp.resolution == "2160p"


class TestAudioTrackResponse:
    def test_from_dict(self):
        data = {
            "id": 1,
            "track_index": 0,
            "codec": "AAC",
            "bitrate": 128000,
            "channel_layout": "2.0",
            "channels": 2,
            "language": "en",
            "track_name": None,
            "is_default": True,
            "is_original": False,
            "is_forced": False,
            "is_commentary": False,
            "is_atmos": False,
            "sample_rate": 48000,
            "compression_mode": "Lossy",
        }
        resp = AudioTrackResponse(**data)
        assert resp.codec == "AAC"
        assert resp.channels == 2


class TestSubtitleTrackResponse:
    def test_from_dict(self):
        data = {
            "id": 1,
            "track_index": 0,
            "codec": "SRT",
            "language": "en",
            "track_name": "English",
            "is_default": True,
            "is_forced": False,
            "is_hearing_impaired": True,
        }
        resp = SubtitleTrackResponse(**data)
        assert resp.is_hearing_impaired is True
