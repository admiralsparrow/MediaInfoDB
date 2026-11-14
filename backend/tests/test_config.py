from unittest.mock import patch

import pytest


class TestSettings:
    def test_allowed_roots_list_single(self):
        with patch.dict("os.environ", {"ALLOWED_BROWSE_ROOTS": "/media"}):
            from app.config import Settings
            s = Settings()
            assert s.allowed_roots_list == ["/media"]

    def test_allowed_roots_list_multiple(self):
        with patch.dict("os.environ", {"ALLOWED_BROWSE_ROOTS": "/media,/data,/mnt/nas"}):
            from app.config import Settings
            s = Settings()
            assert s.allowed_roots_list == ["/media", "/data", "/mnt/nas"]

    def test_allowed_roots_list_strips_whitespace(self):
        with patch.dict("os.environ", {"ALLOWED_BROWSE_ROOTS": " /media , /data "}):
            from app.config import Settings
            s = Settings()
            assert s.allowed_roots_list == ["/media", "/data"]

    def test_allowed_roots_list_empty_entries_skipped(self):
        with patch.dict("os.environ", {"ALLOWED_BROWSE_ROOTS": "/media,,/data"}):
            from app.config import Settings
            s = Settings()
            assert s.allowed_roots_list == ["/media", "/data"]

    def test_sync_database_url(self):
        with patch.dict("os.environ", {"DATABASE_URL": "postgresql+asyncpg://user:pass@host/db"}):
            from app.config import Settings
            s = Settings()
            assert s.sync_database_url == "postgresql://user:pass@host/db"

    def test_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.SCAN_INTERVAL_MINUTES == 360
        assert s.ALLOWED_BROWSE_ROOTS  # not empty
