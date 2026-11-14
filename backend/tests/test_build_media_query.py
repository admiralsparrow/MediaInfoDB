"""Integration tests for build_media_query — exercises all filter types against SQLite."""

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AudioTrack, MediaFile, ScannedFolder, SubtitleTrack, VideoTrack
from app.models.library import Library, library_folders
from app.services.filter_builder import build_media_query, get_filter_options
from tests.conftest import create_test_engine
from app.models.base import Base
from sqlalchemy.ext.asyncio import async_sessionmaker
from datetime import datetime, timezone


@pytest_asyncio.fixture
async def db():
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Seed data
        lib = Library(name="Movies")
        session.add(lib)
        await session.flush()

        folder = ScannedFolder(path="/media/movies", enabled=True, file_count=0)
        session.add(folder)
        await session.flush()

        await session.execute(
            library_folders.insert().values(library_id=lib.id, folder_id=folder.id)
        )

        folder2 = ScannedFolder(path="/media/tv", enabled=True, file_count=0)
        session.add(folder2)
        await session.flush()

        # Media files with different attributes
        mf1 = MediaFile(
            folder_id=folder.id,
            file_path="/media/movies/Movie.A.2020.mkv",
            file_name="Movie.A.2020.mkv",
            container_format="Matroska",
            title="Movie A",
            overall_bitrate=5_000_000,
            year=2020,
            hybrid=False,
            source="BluRay",
            provider="AMZN",
            release_group="GRP1",
            relative_path="Movie.A.2020.mkv",
            scanned_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
            file_modified_at=datetime(2024, 5, 1, tzinfo=timezone.utc),
        )
        mf2 = MediaFile(
            folder_id=folder.id,
            file_path="/media/movies/Movie.B.2021.mkv",
            file_name="Movie.B.2021.mkv",
            container_format="MPEG-4",
            title=None,
            overall_bitrate=3_000_000,
            year=2021,
            hybrid=True,
            source="WEB-DL",
            provider=None,
            release_group="GRP2",
            relative_path="subfolder/Movie.B.2021.mkv",
            scanned_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
            file_modified_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
        )
        mf3 = MediaFile(
            folder_id=folder2.id,
            file_path="/media/tv/Episode.S01E01.mkv",
            file_name="Episode.S01E01.mkv",
            container_format="Matroska",
            overall_bitrate=2_000_000,
            year=2022,
            hybrid=False,
            source="HDTV",
            relative_path="Episode.S01E01.mkv",
            scanned_at=datetime(2024, 8, 1, tzinfo=timezone.utc),
        )
        session.add_all([mf1, mf2, mf3])
        await session.flush()

        # Video tracks
        vt1 = VideoTrack(
            media_file_id=mf1.id, track_index=0, codec="HEVC",
            width=3840, height=2160, bitrate=4_000_000, hdr10=True,
            dolby_vision=True, dv_profile=8, dv_layer="6", hdr10_plus=False,
            language="en", is_default=True, is_forced=False,
            bit_depth=10, resolution="2160p",
        )
        vt2 = VideoTrack(
            media_file_id=mf2.id, track_index=0, codec="AVC",
            width=1920, height=1080, bitrate=2_000_000, hdr10=False,
            dolby_vision=False, hdr10_plus=False,
            language="en", is_default=True, is_forced=False,
            bit_depth=8, resolution="1080p",
        )
        # mf3 has no video tracks (invalid file)
        session.add_all([vt1, vt2])
        await session.flush()

        # Audio tracks
        at1 = AudioTrack(
            media_file_id=mf1.id, track_index=1, codec="TrueHD",
            bitrate=5_000_000, channel_layout="7.1", channels=8,
            language="en", is_default=True, is_atmos=True,
            is_commentary=False, sample_rate=48000, compression_mode="Lossless",
        )
        at2 = AudioTrack(
            media_file_id=mf1.id, track_index=2, codec="AAC",
            bitrate=128_000, channel_layout="2.0", channels=2,
            language="fr", is_default=False, is_atmos=False,
            is_commentary=True, sample_rate=44100, compression_mode="Lossy",
        )
        at3 = AudioTrack(
            media_file_id=mf2.id, track_index=1, codec="AAC",
            bitrate=256_000, channel_layout="5.1", channels=6,
            language="en", is_default=True, is_atmos=False,
            is_commentary=False, sample_rate=48000,
        )
        session.add_all([at1, at2, at3])
        await session.flush()

        # Subtitle tracks
        st1 = SubtitleTrack(
            media_file_id=mf1.id, track_index=3, codec="SRT",
            language="en", is_default=True, is_forced=False, is_hearing_impaired=True,
        )
        st2 = SubtitleTrack(
            media_file_id=mf1.id, track_index=4, codec="SRT",
            language="fr", is_default=False, is_forced=False, is_hearing_impaired=False,
        )
        st3 = SubtitleTrack(
            media_file_id=mf2.id, track_index=2, codec="ASS",
            language="en", is_default=True, is_forced=False, is_hearing_impaired=False,
        )
        session.add_all([st1, st2, st3])
        await session.commit()

        yield session
    await engine.dispose()


async def _execute_query(db: AsyncSession, filters: dict) -> list[MediaFile]:
    query = build_media_query(filters)
    result = await db.execute(query)
    return list(result.scalars().all())


# ── enum filter ──────────────────────────────────────────────────


class TestEnumFilter:
    @pytest.mark.asyncio
    async def test_single_value(self, db):
        results = await _execute_query(db, {"container_format": "Matroska"})
        assert len(results) == 2
        assert all(r.container_format == "Matroska" for r in results)

    @pytest.mark.asyncio
    async def test_multi_value(self, db):
        results = await _execute_query(db, {"container_format": "Matroska,MPEG-4"})
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_inverted(self, db):
        results = await _execute_query(db, {"container_format": "!Matroska"})
        assert len(results) == 1
        assert results[0].container_format == "MPEG-4"

    @pytest.mark.asyncio
    async def test_none_value(self, db):
        results = await _execute_query(db, {"provider": "(none)"})
        assert len(results) == 2
        assert all(r.provider is None for r in results)

    @pytest.mark.asyncio
    async def test_inverted_none(self, db):
        results = await _execute_query(db, {"provider": "!(none)"})
        assert len(results) == 1
        assert results[0].provider is not None

    @pytest.mark.asyncio
    async def test_value_plus_none(self, db):
        results = await _execute_query(db, {"provider": "AMZN,(none)"})
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_year_enum_integer_cast(self, db):
        results = await _execute_query(db, {"year": "2020"})
        assert len(results) == 1
        assert results[0].year == 2020


# ── track enum filter (join) ─────────────────────────────────────


class TestTrackEnumFilter:
    @pytest.mark.asyncio
    async def test_video_codec(self, db):
        results = await _execute_query(db, {"video.codec": "HEVC"})
        assert len(results) == 1
        assert results[0].file_name == "Movie.A.2020.mkv"

    @pytest.mark.asyncio
    async def test_audio_codec_multi(self, db):
        results = await _execute_query(db, {"audio.codec": "TrueHD,AAC"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_inverted_track_enum(self, db):
        results = await _execute_query(db, {"audio.codec": "!TrueHD"})
        # mf2 has only AAC, mf3 has no audio → only mf2 should NOT have TrueHD
        # inverted uses NOT EXISTS subquery, so mf1 (which has TrueHD) is excluded
        names = {r.file_name for r in results}
        assert "Movie.A.2020.mkv" not in names

    @pytest.mark.asyncio
    async def test_subtitle_language(self, db):
        results = await _execute_query(db, {"subtitle.language": "fr"})
        assert len(results) == 1


# ── boolean filter ───────────────────────────────────────────────


class TestBooleanFilter:
    @pytest.mark.asyncio
    async def test_hybrid_true(self, db):
        results = await _execute_query(db, {"hybrid": "true"})
        assert len(results) == 1
        assert results[0].hybrid is True

    @pytest.mark.asyncio
    async def test_hybrid_false(self, db):
        results = await _execute_query(db, {"hybrid": "false"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_track_boolean_hdr10(self, db):
        results = await _execute_query(db, {"video.hdr10": "true"})
        assert len(results) == 1
        assert results[0].file_name == "Movie.A.2020.mkv"

    @pytest.mark.asyncio
    async def test_track_boolean_atmos(self, db):
        results = await _execute_query(db, {"audio.is_atmos": "true"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_track_boolean_commentary(self, db):
        results = await _execute_query(db, {"audio.is_commentary": "true"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_hi_subtitles(self, db):
        results = await _execute_query(db, {"subtitle.is_hearing_impaired": "true"})
        assert len(results) == 1


# ── gte/lte filter ───────────────────────────────────────────────


class TestRangeFilter:
    @pytest.mark.asyncio
    async def test_bitrate_gte(self, db):
        results = await _execute_query(db, {"overall_bitrate_min": "4000000"})
        assert len(results) == 1
        assert results[0].overall_bitrate >= 4_000_000

    @pytest.mark.asyncio
    async def test_bitrate_lte(self, db):
        results = await _execute_query(db, {"overall_bitrate_max": "3000000"})
        assert len(results) == 2
        assert all(r.overall_bitrate <= 3_000_000 for r in results)

    @pytest.mark.asyncio
    async def test_bitrate_range(self, db):
        results = await _execute_query(db, {
            "overall_bitrate_min": "2500000",
            "overall_bitrate_max": "5000000",
        })
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_track_bitrate_gte(self, db):
        results = await _execute_query(db, {"video.bitrate_min": "3000000"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_gte_none_value(self, db):
        results = await _execute_query(db, {"overall_bitrate_min": "(none)"})
        assert all(r.overall_bitrate is None for r in results)


# ── count_gte/count_lte ──────────────────────────────────────────


class TestCountFilter:
    @pytest.mark.asyncio
    async def test_audio_count_gte(self, db):
        results = await _execute_query(db, {"audio.track_count_min": "2"})
        assert len(results) == 1
        assert results[0].file_name == "Movie.A.2020.mkv"

    @pytest.mark.asyncio
    async def test_audio_count_lte(self, db):
        results = await _execute_query(db, {"audio.track_count_max": "1"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_subtitle_count_gte(self, db):
        results = await _execute_query(db, {"subtitle.track_count_min": "2"})
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_subtitle_count_lte(self, db):
        results = await _execute_query(db, {"subtitle.track_count_max": "0"})
        assert len(results) == 1
        assert results[0].file_name == "Episode.S01E01.mkv"


# ── fuzzy filter ─────────────────────────────────────────────────


class TestFuzzyFilter:
    @pytest.mark.asyncio
    async def test_single_token(self, db):
        results = await _execute_query(db, {"search": "Movie"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_multi_token(self, db):
        results = await _execute_query(db, {"search": "Movie A"})
        assert len(results) == 1
        assert results[0].file_name == "Movie.A.2020.mkv"

    @pytest.mark.asyncio
    async def test_case_insensitive(self, db):
        results = await _execute_query(db, {"search": "movie"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_no_match(self, db):
        results = await _execute_query(db, {"search": "nonexistent"})
        assert len(results) == 0


# ── text filter ──────────────────────────────────────────────────


class TestTextFilter:
    @pytest.mark.asyncio
    async def test_title_contains(self, db):
        results = await _execute_query(db, {"title": "Movie"})
        assert len(results) == 1
        assert results[0].title == "Movie A"


# ── prefix filter ────────────────────────────────────────────────


class TestPrefixFilter:
    @pytest.mark.asyncio
    async def test_folder_path_prefix(self, db):
        results = await _execute_query(db, {"folder_path": "subfolder"})
        assert len(results) == 1
        assert results[0].file_name == "Movie.B.2021.mkv"

    @pytest.mark.asyncio
    async def test_folder_path_no_match(self, db):
        results = await _execute_query(db, {"folder_path": "nonexistent"})
        assert len(results) == 0


# ── date filter ──────────────────────────────────────────────────


class TestDateFilter:
    @pytest.mark.asyncio
    async def test_scanned_at_min(self, db):
        results = await _execute_query(db, {"scanned_at_min": "2024-07-01", "tz_offset": "0"})
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_scanned_at_max(self, db):
        results = await _execute_query(db, {"scanned_at_max": "2024-06-15", "tz_offset": "0"})
        assert len(results) == 1
        assert results[0].file_name == "Movie.A.2020.mkv"

    @pytest.mark.asyncio
    async def test_file_modified_at_range(self, db):
        results = await _execute_query(db, {
            "file_modified_at_min": "2024-05-01",
            "file_modified_at_max": "2024-06-01",
            "tz_offset": "0",
        })
        assert len(results) == 1
        assert results[0].file_name == "Movie.A.2020.mkv"

    @pytest.mark.asyncio
    async def test_tz_offset_applied(self, db):
        results = await _execute_query(db, {
            "scanned_at_min": "2024-06-01",
            "tz_offset": "-720",
        })
        assert len(results) >= 1


# ── library_id filter ────────────────────────────────────────────


class TestLibraryFilter:
    @pytest.mark.asyncio
    async def test_library_id(self, db):
        results = await _execute_query(db, {"library_id": "1"})
        assert len(results) == 2
        names = {r.file_name for r in results}
        assert "Episode.S01E01.mkv" not in names

    @pytest.mark.asyncio
    async def test_folder_id(self, db):
        folder = (await db.execute(
            select(ScannedFolder).where(ScannedFolder.path == "/media/tv")
        )).scalar_one()
        results = await _execute_query(db, {"folder_id": str(folder.id)})
        assert len(results) == 1
        assert results[0].file_name == "Episode.S01E01.mkv"


# ── invalid filter ───────────────────────────────────────────────


class TestInvalidFilter:
    @pytest.mark.asyncio
    async def test_invalid_true(self, db):
        results = await _execute_query(db, {"invalid": "true"})
        assert len(results) == 1
        assert results[0].file_name == "Episode.S01E01.mkv"

    @pytest.mark.asyncio
    async def test_invalid_false(self, db):
        results = await _execute_query(db, {"invalid": "false"})
        assert len(results) == 2


# ── combined filters ─────────────────────────────────────────────


class TestCombinedFilters:
    @pytest.mark.asyncio
    async def test_enum_plus_boolean(self, db):
        results = await _execute_query(db, {
            "video.codec": "HEVC",
            "video.hdr10": "true",
        })
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_plus_range(self, db):
        results = await _execute_query(db, {
            "search": "Movie",
            "overall_bitrate_min": "4000000",
        })
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_empty_filters(self, db):
        results = await _execute_query(db, {})
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_unknown_params_ignored(self, db):
        results = await _execute_query(db, {"nonexistent_param": "foo"})
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_empty_value_ignored(self, db):
        results = await _execute_query(db, {"video.codec": ""})
        assert len(results) == 3


# ── get_filter_options ───────────────────────────────────────────


class TestGetFilterOptions:
    @pytest.mark.asyncio
    async def test_returns_dict(self, db):
        options = await get_filter_options(db)
        assert isinstance(options, dict)

    @pytest.mark.asyncio
    async def test_contains_expected_keys(self, db):
        options = await get_filter_options(db)
        assert "container_format" in options
        assert "video.codec" in options
        assert "audio.codec" in options

    @pytest.mark.asyncio
    async def test_values_are_strings(self, db):
        options = await get_filter_options(db)
        for key, values in options.items():
            for v in values:
                assert isinstance(v, str)

    @pytest.mark.asyncio
    async def test_none_placeholder(self, db):
        options = await get_filter_options(db)
        if "provider" in options:
            assert "(none)" in options["provider"]

    @pytest.mark.asyncio
    async def test_library_id_filter(self, db):
        options = await get_filter_options(db, library_id=1)
        assert isinstance(options, dict)
