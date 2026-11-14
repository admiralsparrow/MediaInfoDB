"""Tests for scan_file() with mocked pymediainfo."""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.scanner import scan_file


def _make_track(track_type, **kwargs):
    defaults = {
        "format": None, "title": None, "duration": None, "overall_bit_rate": None,
        "bit_rate": None, "nominal_bit_rate": None, "maximum_bit_rate": None,
        "stream_size": None, "width": None, "height": None, "frame_rate": None,
        "language": None, "default": None, "forced": None, "channel_s": None,
        "channel_layout": None, "stream_identifier": None, "streamorder": "0",
        "hdr_format": None, "hdr_format_level": None, "hdr_format_profile": None,
        "hdr_format_compatibility": None, "transfer_characteristics": None,
        "display_aspect_ratio": None, "bit_depth": None, "color_primaries": None,
        "encoded_library_name": None, "writing_library": None, "scan_type": None,
        "chroma_subsampling": None, "format_commercial_name": None,
        "format_additionalfeatures": None, "original": None, "sampling_rate": None,
        "compression_mode": None,
    }
    defaults.update(kwargs)
    defaults["track_type"] = track_type
    return SimpleNamespace(**defaults)


def _mock_parse(tracks):
    mi = MagicMock()
    mi.tracks = tracks
    return mi


class TestScanFileBasic:
    @patch("app.services.scanner.os.path.getsize", return_value=1_000_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_returns_media_file(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "movie.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska", title="Test Movie",
                        overall_bit_rate="5000000", duration="7200000"),
            _make_track("Video", format="HEVC", bit_rate="4000000",
                        width="3840", height="2160", frame_rate="23.976",
                        default="Yes", bit_depth="10", hdr_format="HDR10",
                        transfer_characteristics="PQ"),
            _make_track("Audio", format="TrueHD", bit_rate="5000000",
                        channel_s="8", channel_layout="L R C LFE Ls Rs Lb Rb",
                        language="en", default="Yes",
                        format_commercial_name="Dolby TrueHD with Dolby Atmos"),
            _make_track("Text", format="SRT", language="en", default="Yes"),
        ])

        result = scan_file(str(f))

        assert result is not None
        assert result.file_name == "movie.mkv"
        assert result.container_format == "Matroska"
        assert result.title == "Test Movie"
        assert result.overall_bitrate == 5_000_000
        assert result.duration_ms == 7_200_000
        assert result.file_size_bytes == 1_000_000
        assert result.stream_count == 3
        assert len(result.video_tracks) == 1
        assert len(result.audio_tracks) == 1
        assert len(result.subtitle_tracks) == 1

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_video_track_details(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "test.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Video", format="HEVC", bit_rate="4000000",
                        width="3840", height="2160", frame_rate="23.976",
                        default="Yes", bit_depth="10",
                        hdr_format="SMPTE ST 2086, HDR10 compatible",
                        hdr_format_profile="dvhe.08",
                        hdr_format_level="06",
                        display_aspect_ratio="1.778",
                        color_primaries="BT.2020",
                        transfer_characteristics="PQ",
                        encoded_library_name="x265",
                        scan_type="Progressive",
                        chroma_subsampling="4:2:0"),
        ])

        result = scan_file(str(f))
        vt = result.video_tracks[0]

        assert vt.codec == "HEVC"
        assert vt.bitrate == 4_000_000
        assert vt.width == 3840
        assert vt.height == 2160
        assert vt.framerate == 23.976
        assert vt.is_default is True
        assert vt.bit_depth == 10
        assert vt.hdr10 is True
        assert vt.dolby_vision is False
        assert vt.dv_profile == 8
        assert vt.dv_layer == "6"
        assert vt.display_aspect_ratio == "1.78:1"
        assert vt.color_primaries == "BT.2020"
        assert vt.encoding_library == "x265"
        assert vt.scan_type == "Progressive"
        assert vt.chroma_subsampling == "4:2:0"
        assert vt.resolution == "2160p"

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_audio_track_details(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "test.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Audio", format="E-AC-3", bit_rate="768000",
                        channel_s="6", channel_layout="L R C LFE Ls Rs",
                        language="en", default="Yes", original="Yes",
                        title="Director Commentary",
                        format_additionalfeatures="JOC",
                        sampling_rate="48000", compression_mode="Lossy"),
        ])

        result = scan_file(str(f))
        at = result.audio_tracks[0]

        assert at.codec == "E-AC-3"
        assert at.bitrate == 768_000
        assert at.channels == 6
        assert at.channel_layout == "5.1"
        assert at.language == "en"
        assert at.is_default is True
        assert at.is_original is True
        assert at.is_commentary is True
        assert at.is_atmos is True
        assert at.sample_rate == 48000
        assert at.compression_mode == "Lossy"

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_subtitle_track_details(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "test.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Text", format="ASS", language="en",
                        default="Yes", forced="Yes",
                        title="English SDH"),
        ])

        result = scan_file(str(f))
        st = result.subtitle_tracks[0]

        assert st.codec == "ASS"
        assert st.language == "en"
        assert st.is_default is True
        assert st.is_forced is True
        assert st.is_hearing_impaired is True

    @patch("app.services.scanner.MediaInfo.parse", side_effect=Exception("parse error"))
    def test_parse_error_returns_none(self, mock_parse, tmp_path):
        f = tmp_path / "broken.mkv"
        f.touch()
        result = scan_file(str(f))
        assert result is None


class TestScanFileMetadata:
    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_release_group_parsed(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "Movie.2020.BluRay.REMUX-FraMeSToR.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
        ])
        result = scan_file(str(f))
        assert result.release_group == "FraMeSToR"

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_source_parsed(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "Movie.2020.BluRay.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
        ])
        result = scan_file(str(f))
        assert result.source == "BluRay"

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_year_parsed(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "Movie.2020.BluRay.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
        ])
        result = scan_file(str(f))
        assert result.year == 2020

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_provider_parsed(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "Movie.2020.AMZN.WEB-DL.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
        ])
        result = scan_file(str(f))
        assert result.provider == "AMZN"

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_hybrid_parsed(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "Movie.2020.Hybrid.BluRay.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
        ])
        result = scan_file(str(f))
        assert result.hybrid is True


class TestScanFileBitrateFallback:
    @patch("app.services.scanner.os.path.getsize", return_value=1_000_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_overall_bitrate_from_file_size_duration(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "test.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska", duration="8000"),
        ])
        result = scan_file(str(f))
        assert result.overall_bitrate == int((1_000_000 * 8) / (8000 / 1000))

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_no_video_tracks(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "audio.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Audio", format="FLAC", channel_s="2",
                        channel_layout="L R", language="en"),
        ])
        result = scan_file(str(f))
        assert result.stream_count == 1
        assert len(result.video_tracks) == 0
        assert len(result.audio_tracks) == 1


class TestScanFileDolbyVision:
    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_dv_profile_from_hdr_format(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "dv.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Video", format="HEVC",
                        hdr_format="Dolby Vision, Version 1.0, dvhe.08.06, BL+RPU",
                        hdr_format_profile="dvhe.08",
                        hdr_format_level="06"),
        ])
        result = scan_file(str(f))
        vt = result.video_tracks[0]
        assert vt.dolby_vision is True
        assert vt.dv_profile == 8
        assert vt.dv_layer == "6"

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_hdr10_plus_detected(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "hdr10plus.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Video", format="HEVC",
                        hdr_format="HDR10+ Profile A",
                        hdr_format_compatibility="HDR10+"),
        ])
        result = scan_file(str(f))
        vt = result.video_tracks[0]
        assert vt.hdr10_plus is True

    @patch("app.services.scanner.os.path.getsize", return_value=500_000)
    @patch("app.services.scanner.MediaInfo.parse")
    def test_dv_with_hdr10_compat(self, mock_parse, _mock_size, tmp_path):
        f = tmp_path / "dv_hdr10.mkv"
        f.touch()
        mock_parse.return_value = _mock_parse([
            _make_track("General", format="Matroska"),
            _make_track("Video", format="HEVC",
                        hdr_format="Dolby Vision / SMPTE ST 2086, HDR10 compatible",
                        hdr_format_profile="dvhe.08",
                        hdr_format_level="06",
                        transfer_characteristics="PQ"),
        ])
        result = scan_file(str(f))
        vt = result.video_tracks[0]
        assert vt.dolby_vision is True
        assert vt.hdr10 is True
