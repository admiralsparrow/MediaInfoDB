import pytest
from fastapi import HTTPException

from app.services.filter_builder import (
    FILTER_REGISTRY,
    _escape_like,
    _safe_date,
    _safe_int,
)
from app.models import AudioTrack, MediaFile, SubtitleTrack, VideoTrack


class TestSafeInt:
    def test_valid_integer(self):
        assert _safe_int("42", "test") == 42

    def test_negative(self):
        assert _safe_int("-1", "test") == -1

    def test_invalid_raises_http_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _safe_int("abc", "my_param")
        assert exc_info.value.status_code == 400
        assert "my_param" in exc_info.value.detail

    def test_empty_raises(self):
        with pytest.raises(HTTPException):
            _safe_int("", "test")

    def test_float_string_raises(self):
        with pytest.raises(HTTPException):
            _safe_int("3.14", "test")


class TestSafeDate:
    def test_valid_date(self):
        dt = _safe_date("2024-06-15", "test")
        assert dt.year == 2024
        assert dt.month == 6
        assert dt.day == 15
        assert dt.hour == 0 and dt.minute == 0

    def test_with_tz_offset(self):
        dt = _safe_date("2024-06-15", "test", tz_offset_minutes=300)
        assert dt.hour == 5
        assert dt.minute == 0

    def test_negative_tz_offset(self):
        dt = _safe_date("2024-06-15", "test", tz_offset_minutes=-480)
        # midnight - 8h wraps to previous day
        assert dt.day == 14
        assert dt.hour == 16

    def test_invalid_raises_http_400(self):
        with pytest.raises(HTTPException) as exc_info:
            _safe_date("not-a-date", "my_param")
        assert exc_info.value.status_code == 400
        assert "my_param" in exc_info.value.detail


class TestEscapeLike:
    def test_no_special_chars(self):
        assert _escape_like("hello") == "hello"

    def test_escapes_percent(self):
        assert _escape_like("100%") == "100\\%"

    def test_escapes_underscore(self):
        assert _escape_like("file_name") == "file\\_name"

    def test_escapes_backslash(self):
        assert _escape_like("a\\b") == "a\\\\b"

    def test_all_special(self):
        assert _escape_like("\\%_") == "\\\\\\%\\_"


class TestFilterRegistry:
    def test_all_models_are_valid(self):
        valid_models = {MediaFile, VideoTrack, AudioTrack, SubtitleTrack}
        for param, (model, col_name, _) in FILTER_REGISTRY.items():
            assert model in valid_models, f"Filter '{param}' uses unknown model {model}"

    def test_all_columns_exist(self):
        for param, (model, col_name, _) in FILTER_REGISTRY.items():
            assert hasattr(model, col_name), (
                f"Filter '{param}': {model.__name__} has no column '{col_name}'"
            )

    def test_filter_types_are_valid(self):
        valid_types = {"enum", "boolean", "gte", "lte", "text", "prefix", "fuzzy",
                       "count_gte", "count_lte", "date_gte", "date_lte"}
        for param, (_, _, filter_type) in FILTER_REGISTRY.items():
            assert filter_type in valid_types, (
                f"Filter '{param}' has unknown type '{filter_type}'"
            )

    def test_registry_has_expected_filters(self):
        assert "search" in FILTER_REGISTRY
        assert "video.codec" in FILTER_REGISTRY
        assert "audio.codec" in FILTER_REGISTRY
        assert "subtitle.language" in FILTER_REGISTRY
        assert "source" in FILTER_REGISTRY
        assert "provider" in FILTER_REGISTRY
