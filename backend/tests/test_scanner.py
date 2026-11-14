import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.scanner import (
    VIDEO_EXTENSIONS,
    _compute_resolution,
    _detect_atmos,
    _detect_commentary,
    _detect_dolby_vision,
    _detect_hdr10,
    _detect_hdr10_plus,
    _detect_hearing_impaired,
    _float_or_none,
    _format_aspect_ratio,
    _get_bitrate,
    _get_dv_layer,
    _get_dv_profile,
    _get_encoding_library,
    _int_or_none,
    _is_yes,
    _normalize_channel_layout,
    _parse_hybrid,
    _parse_release_group,
    _parse_source,
    _parse_year,
    _track_index,
    find_video_files,
)


class TestIntOrNone:
    @pytest.mark.parametrize("val, expected", [
        (None, None),
        (42, 42),
        ("100", 100),
        ("3.7", 3),
        ("abc", None),
        ("", None),
    ])
    def test_values(self, val, expected):
        assert _int_or_none(val) == expected


class TestFloatOrNone:
    @pytest.mark.parametrize("val, expected", [
        (None, None),
        (3.14, 3.14),
        ("23.976", 23.976),
        ("abc", None),
    ])
    def test_values(self, val, expected):
        result = _float_or_none(val)
        if expected is None:
            assert result is None
        else:
            assert abs(result - expected) < 0.001


class TestIsYes:
    @pytest.mark.parametrize("val, expected", [
        (None, False),
        ("Yes", True),
        ("yes", True),
        ("true", True),
        ("True", True),
        ("1", True),
        ("No", False),
        ("false", False),
        ("0", False),
        ("", False),
    ])
    def test_values(self, val, expected):
        assert _is_yes(val) == expected


class TestDetectHDR10:
    def test_hdr10_in_hdr_format(self):
        track = SimpleNamespace(hdr_format="HDR10", transfer_characteristics="")
        assert _detect_hdr10(track) is True

    def test_pq_in_transfer(self):
        track = SimpleNamespace(hdr_format="", transfer_characteristics="PQ")
        assert _detect_hdr10(track) is True

    def test_smpte_st_2084_pq(self):
        track = SimpleNamespace(hdr_format="", transfer_characteristics="SMPTE ST 2084 PQ")
        assert _detect_hdr10(track) is True

    def test_no_hdr10(self):
        track = SimpleNamespace(hdr_format="", transfer_characteristics="BT.709")
        assert _detect_hdr10(track) is False

    def test_none_attributes(self):
        track = SimpleNamespace(hdr_format=None, transfer_characteristics=None)
        assert _detect_hdr10(track) is False


class TestDetectDolbyVision:
    def test_dv_present(self):
        track = SimpleNamespace(hdr_format="Dolby Vision, Version 1.0")
        assert _detect_dolby_vision(track) is True

    def test_dv_absent(self):
        track = SimpleNamespace(hdr_format="HDR10")
        assert _detect_dolby_vision(track) is False

    def test_none(self):
        track = SimpleNamespace(hdr_format=None)
        assert _detect_dolby_vision(track) is False


class TestGetDvLayer:
    def test_extracts_layer(self):
        track = SimpleNamespace(hdr_format_level="06")
        assert _get_dv_layer(track) == "6"

    def test_no_level(self):
        track = SimpleNamespace(hdr_format_level="")
        assert _get_dv_layer(track) is None

    def test_none_level(self):
        track = SimpleNamespace(hdr_format_level=None)
        assert _get_dv_layer(track) is None


class TestGetDvProfile:
    def test_extracts_from_profile_string(self):
        track = SimpleNamespace(hdr_format_profile="dvhe.05", hdr_format="")
        assert _get_dv_profile(track) == 5

    def test_extracts_from_hdr_format(self):
        track = SimpleNamespace(hdr_format_profile="", hdr_format="dvhe.08.06")
        assert _get_dv_profile(track) == 8

    def test_extracts_profile_keyword(self):
        track = SimpleNamespace(hdr_format_profile="", hdr_format="Dolby Vision profile 7")
        assert _get_dv_profile(track) == 7

    def test_no_profile(self):
        track = SimpleNamespace(hdr_format_profile="", hdr_format="HDR10")
        assert _get_dv_profile(track) is None


class TestDetectHDR10Plus:
    def test_present_in_hdr_format(self):
        track = SimpleNamespace(hdr_format="HDR10+", hdr_format_compatibility="")
        assert _detect_hdr10_plus(track) is True

    def test_present_in_compatibility(self):
        track = SimpleNamespace(hdr_format="", hdr_format_compatibility="HDR10+")
        assert _detect_hdr10_plus(track) is True

    def test_absent(self):
        track = SimpleNamespace(hdr_format="HDR10", hdr_format_compatibility="")
        assert _detect_hdr10_plus(track) is False


class TestNormalizeChannelLayout:
    def test_stereo(self):
        track = SimpleNamespace(channel_s=2, channel_layout="L R")
        assert _normalize_channel_layout(track) == "2.0"

    def test_5_1(self):
        track = SimpleNamespace(channel_s=6, channel_layout="L R C LFE Ls Rs")
        assert _normalize_channel_layout(track) == "5.1"

    def test_7_1(self):
        track = SimpleNamespace(channel_s=8, channel_layout="L R C LFE Ls Rs Lb Rb")
        assert _normalize_channel_layout(track) == "7.1"

    def test_atmos_overhead_channels(self):
        track = SimpleNamespace(channel_s=16, channel_layout="L R C LFE Ls Rs Lb Rb Tfl Tfr Tbl Tbr Tsl Tsr Tfc Tbc")
        result = _normalize_channel_layout(track)
        assert result == "7.1.8"

    def test_7_1_4_atmos(self):
        track = SimpleNamespace(channel_s=12, channel_layout="L R C LFE Ls Rs Lb Rb Tfl Tfr Tbl Tbr")
        result = _normalize_channel_layout(track)
        assert result == "7.1.4"

    def test_no_layout_string_uses_fallback(self):
        track = SimpleNamespace(channel_s=6, channel_layout="")
        assert _normalize_channel_layout(track) == "5.1"

    def test_none_channels(self):
        track = SimpleNamespace(channel_s=None, channel_layout="")
        assert _normalize_channel_layout(track) is None

    def test_mono(self):
        track = SimpleNamespace(channel_s=1, channel_layout="C")
        assert _normalize_channel_layout(track) == "1.0"

    def test_unknown_channel_count(self):
        track = SimpleNamespace(channel_s=3, channel_layout="")
        assert _normalize_channel_layout(track) == "3.0"


class TestDetectAtmos:
    def test_commercial_name(self):
        track = SimpleNamespace(format_commercial_name="Dolby Digital Plus with Dolby Atmos", title="", format_additionalfeatures="")
        assert _detect_atmos(track) is True

    def test_title(self):
        track = SimpleNamespace(format_commercial_name="", title="Surround 7.1 Atmos", format_additionalfeatures="")
        assert _detect_atmos(track) is True

    def test_joc(self):
        track = SimpleNamespace(format_commercial_name="", title="", format_additionalfeatures="JOC")
        assert _detect_atmos(track) is True

    def test_no_atmos(self):
        track = SimpleNamespace(format_commercial_name="DTS-HD Master Audio", title="Surround 7.1", format_additionalfeatures="")
        assert _detect_atmos(track) is False


class TestDetectCommentary:
    @pytest.mark.parametrize("title, expected", [
        ("Director's Commentary", True),
        ("Commentary with Cast", True),
        ("Audio Comment Track", True),
        ("English 5.1", False),
        ("", False),
        (None, False),
    ])
    def test_values(self, title, expected):
        track = SimpleNamespace(title=title)
        assert _detect_commentary(track) == expected


class TestDetectHearingImpaired:
    @pytest.mark.parametrize("title, expected", [
        ("English (SDH)", True),
        ("English SDH", True),
        ("Hearing Impaired", True),
        ("English HI", True),
        ("English", False),
        ("", False),
    ])
    def test_values(self, title, expected):
        track = SimpleNamespace(title=title)
        assert _detect_hearing_impaired(track) == expected


class TestParseReleaseGroup:
    @pytest.mark.parametrize("filename, expected", [
        ("Movie.2024.1080p.BluRay.x264-GROUP.mkv", "GROUP"),
        ("Show.S01E01.WEB-DL.H.264-FGT.mkv", "FGT"),
        ("Show.S01E01.WEB-DL.H.264-DON).mkv", "DON"),
        ("no_group_here.mkv", None),
    ])
    def test_values(self, filename, expected):
        assert _parse_release_group(filename) == expected


class TestParseSource:
    @pytest.mark.parametrize("filename, expected", [
        ("Movie.2024.1080p.REMUX.mkv", "REMUX"),
        ("Show.S01E01.WEB-DL.H.264-GROUP.mkv", "WEB-DL"),
        ("Show.S01E01.WEBRip.H.264-GROUP.mkv", "WEBRip"),
        ("Movie.2024.BluRay.x264-GROUP.mkv", "BluRay"),
        ("Movie.2024.Blu-Ray.x264-GROUP.mkv", "BluRay"),
        ("Movie.2024.BDRip.x264-GROUP.mkv", "BDRip"),
        ("Movie.DVDRip.x264-GROUP.mkv", "DVDRip"),
        ("Movie.DVD.x264-GROUP.mkv", "DVD"),
        ("Show.S01E01.HDTV.x264-GROUP.mkv", "HDTV"),
        ("random_file.mkv", None),
    ])
    def test_values(self, filename, expected):
        assert _parse_source(filename) == expected

    def test_remux_takes_priority_over_bluray(self):
        assert _parse_source("Movie.2024.BluRay.REMUX.mkv") == "REMUX"


class TestParseYear:
    @pytest.mark.parametrize("filename, path, expected", [
        ("Movie.2024.1080p.BluRay.mkv", "/media/movies/Movie.2024.1080p.BluRay.mkv", 2024),
        ("Movie (2019).mkv", "/media/movies/Movie (2019).mkv", 2019),
        ("Show.S01E01.mkv", "/media/tv/Show (2020)/Season 1/Show.S01E01.mkv", 2020),
        ("no_year.mkv", "/media/movies/no_year.mkv", None),
        ("Movie.1899.BluRay.mkv", "/media/movies/Movie.1899.BluRay.mkv", None),
    ])
    def test_values(self, filename, path, expected):
        assert _parse_year(filename, path) == expected

    def test_year_before_release_info_only(self):
        result = _parse_year("Movie.2023.2160p.WEB-DL.mkv", "/media/Movie.2023.2160p.WEB-DL.mkv")
        assert result == 2023


class TestParseHybrid:
    def test_hybrid_present(self):
        assert _parse_hybrid("Movie.2024.HYBRID.BluRay.mkv", "/media/movies/Movie.2024.HYBRID.BluRay.mkv") is True

    def test_hybrid_absent(self):
        assert _parse_hybrid("Movie.2024.BluRay.mkv", "/media/movies/Movie.2024.BluRay.mkv") is False

    def test_hybrid_in_parent_dir(self):
        assert _parse_hybrid("Movie.mkv", "/media/movies/Movie.2024.HYBRID/Movie.mkv") is True


class TestFormatAspectRatio:
    @pytest.mark.parametrize("val, expected", [
        (None, None),
        (1.778, "1.78:1"),
        ("2.35", "2.35:1"),
        ("abc", "abc"),
        ("", None),
    ])
    def test_values(self, val, expected):
        assert _format_aspect_ratio(val) == expected


class TestComputeResolution:
    @pytest.mark.parametrize("height, width, expected", [
        (2160, 3840, "2160p"),
        (1080, 1920, "1080p"),
        (720, 1280, "720p"),
        (480, 854, "480p"),
        (None, None, None),
        (360, 640, "SD"),
        (1080, None, "1080p"),
        (None, 1920, "1080p"),
        (2000, 3840, "2160p"),  # within 90% tolerance
        (1944, 3456, "2160p"),  # exactly 90% of 2160
    ])
    def test_values(self, height, width, expected):
        assert _compute_resolution(height, width) == expected


class TestGetEncodingLibrary:
    def test_encoded_library_name(self):
        track = SimpleNamespace(encoded_library_name="x265", writing_library=None)
        assert _get_encoding_library(track) == "x265"

    def test_writing_library_fallback(self):
        track = SimpleNamespace(encoded_library_name=None, writing_library="x264 core 164 r3095")
        assert _get_encoding_library(track) == "x264"

    def test_none(self):
        track = SimpleNamespace(encoded_library_name=None, writing_library=None)
        assert _get_encoding_library(track) is None


class TestFindVideoFiles:
    def test_finds_video_extensions(self, tmp_path):
        (tmp_path / "movie.mkv").touch()
        (tmp_path / "movie.mp4").touch()
        (tmp_path / "readme.txt").touch()
        (tmp_path / "image.jpg").touch()
        (tmp_path / "sub" ).mkdir()
        (tmp_path / "sub" / "episode.avi").touch()

        result = find_video_files(str(tmp_path))
        names = [os.path.basename(f) for f in result]
        assert "movie.mkv" in names
        assert "movie.mp4" in names
        assert "episode.avi" in names
        assert "readme.txt" not in names
        assert "image.jpg" not in names

    def test_returns_sorted(self, tmp_path):
        (tmp_path / "z.mkv").touch()
        (tmp_path / "a.mkv").touch()
        (tmp_path / "m.mkv").touch()
        result = find_video_files(str(tmp_path))
        assert result == sorted(result)

    def test_empty_directory(self, tmp_path):
        assert find_video_files(str(tmp_path)) == []

    def test_all_video_extensions(self, tmp_path):
        for ext in VIDEO_EXTENSIONS:
            (tmp_path / f"file{ext}").touch()
        result = find_video_files(str(tmp_path))
        assert len(result) == len(VIDEO_EXTENSIONS)

    def test_case_insensitive_extensions(self, tmp_path):
        (tmp_path / "movie.MKV").touch()
        (tmp_path / "movie.Mp4").touch()
        result = find_video_files(str(tmp_path))
        assert len(result) == 2


class TestGetBitrate:
    def test_bit_rate(self):
        track = SimpleNamespace(bit_rate=5000000, nominal_bit_rate=None, maximum_bit_rate=None, stream_size=None, duration=None, overall_bit_rate=None)
        assert _get_bitrate(track) == 5000000

    def test_overall_bit_rate(self):
        track = SimpleNamespace(overall_bit_rate=10000000, bit_rate=None, nominal_bit_rate=None, maximum_bit_rate=None, stream_size=None, duration=None)
        assert _get_bitrate(track, overall=True) == 10000000

    def test_nominal_fallback(self):
        track = SimpleNamespace(bit_rate=None, nominal_bit_rate=768000, maximum_bit_rate=None, stream_size=None, duration=None, overall_bit_rate=None)
        assert _get_bitrate(track) == 768000

    def test_maximum_fallback(self):
        track = SimpleNamespace(bit_rate=None, nominal_bit_rate=None, maximum_bit_rate=1500000, stream_size=None, duration=None, overall_bit_rate=None)
        assert _get_bitrate(track) == 1500000

    def test_calculated_from_stream_size(self):
        track = SimpleNamespace(bit_rate=None, nominal_bit_rate=None, maximum_bit_rate=None, stream_size=1000000, duration=8000.0, overall_bit_rate=None)
        result = _get_bitrate(track)
        assert result == 1000000

    def test_none_when_nothing_available(self):
        track = SimpleNamespace(bit_rate=None, nominal_bit_rate=None, maximum_bit_rate=None, stream_size=None, duration=None, overall_bit_rate=None)
        assert _get_bitrate(track) is None

    def test_overall_false_ignores_overall(self):
        track = SimpleNamespace(overall_bit_rate=10000000, bit_rate=5000000, nominal_bit_rate=None, maximum_bit_rate=None, stream_size=None, duration=None)
        assert _get_bitrate(track, overall=False) == 5000000


class TestTrackIndex:
    def test_stream_identifier(self):
        track = SimpleNamespace(stream_identifier=2, streamorder=None)
        assert _track_index(track) == 2

    def test_streamorder_fallback(self):
        track = SimpleNamespace(stream_identifier=None, streamorder=3)
        assert _track_index(track) == 3

    def test_defaults_to_zero(self):
        track = SimpleNamespace(stream_identifier=None, streamorder=None)
        assert _track_index(track) == 0


class TestVideoExtensions:
    def test_common_extensions_present(self):
        for ext in [".mkv", ".mp4", ".avi", ".mov", ".ts", ".m2ts"]:
            assert ext in VIDEO_EXTENSIONS

    def test_non_video_extensions_absent(self):
        for ext in [".srt", ".nfo", ".jpg", ".txt", ".exe"]:
            assert ext not in VIDEO_EXTENSIONS
