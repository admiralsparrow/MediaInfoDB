import re
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import Integer, Select, and_, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AudioTrack, MediaFile, ScannedFolder, SubtitleTrack, VideoTrack
from app.models.library import library_folders


def _safe_int(value: str, param_name: str) -> int:
    try:
        return int(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid integer for '{param_name}': {value}")


def _safe_date(value: str, param_name: str, tz_offset_minutes: int = 0) -> datetime:
    try:
        midnight_local = datetime.combine(date.fromisoformat(value), datetime.min.time())
        return midnight_local + timedelta(minutes=tz_offset_minutes)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"Invalid date for '{param_name}': {value}")


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

FILTER_REGISTRY: dict[str, tuple[type, str, str]] = {
    "search": (MediaFile, "file_name", "fuzzy"),
    "folder_path": (MediaFile, "relative_path", "prefix"),
    "container_format": (MediaFile, "container_format", "enum"),
    "title": (MediaFile, "title", "text"),
    "overall_bitrate_min": (MediaFile, "overall_bitrate", "gte"),
    "overall_bitrate_max": (MediaFile, "overall_bitrate", "lte"),
    "release_group": (MediaFile, "release_group", "enum"),
    "source": (MediaFile, "source", "enum"),
    "provider": (MediaFile, "provider", "enum"),
    "year": (MediaFile, "year", "enum"),
    "hybrid": (MediaFile, "hybrid", "boolean"),
    "video.codec": (VideoTrack, "codec", "enum"),
    "video.bitrate_min": (VideoTrack, "bitrate", "gte"),
    "video.bitrate_max": (VideoTrack, "bitrate", "lte"),
    "video.width_min": (VideoTrack, "width", "gte"),
    "video.width_max": (VideoTrack, "width", "lte"),
    "video.height_min": (VideoTrack, "height", "gte"),
    "video.height_max": (VideoTrack, "height", "lte"),
    "video.resolution": (VideoTrack, "resolution", "enum"),
    "video.hdr10": (VideoTrack, "hdr10", "boolean"),
    "video.dolby_vision": (VideoTrack, "dolby_vision", "boolean"),
    "video.dv_profile": (VideoTrack, "dv_profile", "enum"),
    "video.dv_layer": (VideoTrack, "dv_layer", "enum"),
    "video.hdr10_plus": (VideoTrack, "hdr10_plus", "boolean"),
    "video.language": (VideoTrack, "language", "enum"),
    "video.is_default": (VideoTrack, "is_default", "boolean"),
    "video.is_forced": (VideoTrack, "is_forced", "boolean"),
    "video.display_aspect_ratio": (VideoTrack, "display_aspect_ratio", "enum"),
    "video.bit_depth": (VideoTrack, "bit_depth", "enum"),
    "video.color_primaries": (VideoTrack, "color_primaries", "enum"),
    "video.transfer_characteristics": (VideoTrack, "transfer_characteristics", "enum"),
    "video.encoding_library": (VideoTrack, "encoding_library", "enum"),
    "video.scan_type": (VideoTrack, "scan_type", "enum"),
    "video.chroma_subsampling": (VideoTrack, "chroma_subsampling", "enum"),
    "audio.codec": (AudioTrack, "codec", "enum"),
    "audio.bitrate_min": (AudioTrack, "bitrate", "gte"),
    "audio.bitrate_max": (AudioTrack, "bitrate", "lte"),
    "audio.channel_layout": (AudioTrack, "channel_layout", "enum"),
    "audio.language": (AudioTrack, "language", "enum"),
    "audio.is_default": (AudioTrack, "is_default", "boolean"),
    "audio.is_original": (AudioTrack, "is_original", "boolean"),
    "audio.is_forced": (AudioTrack, "is_forced", "boolean"),
    "audio.is_commentary": (AudioTrack, "is_commentary", "boolean"),
    "audio.is_atmos": (AudioTrack, "is_atmos", "boolean"),
    "audio.sample_rate": (AudioTrack, "sample_rate", "enum"),
    "audio.compression_mode": (AudioTrack, "compression_mode", "enum"),
    "subtitle.codec": (SubtitleTrack, "codec", "enum"),
    "subtitle.language": (SubtitleTrack, "language", "enum"),
    "subtitle.is_default": (SubtitleTrack, "is_default", "boolean"),
    "subtitle.is_forced": (SubtitleTrack, "is_forced", "boolean"),
    "subtitle.is_hearing_impaired": (SubtitleTrack, "is_hearing_impaired", "boolean"),
    "audio.track_count_min": (AudioTrack, "media_file_id", "count_gte"),
    "audio.track_count_max": (AudioTrack, "media_file_id", "count_lte"),
    "subtitle.track_count_min": (SubtitleTrack, "media_file_id", "count_gte"),
    "subtitle.track_count_max": (SubtitleTrack, "media_file_id", "count_lte"),
    "scanned_at_min": (MediaFile, "scanned_at", "date_gte"),
    "scanned_at_max": (MediaFile, "scanned_at", "date_lte"),
    "file_modified_at_min": (MediaFile, "file_modified_at", "date_gte"),
    "file_modified_at_max": (MediaFile, "file_modified_at", "date_lte"),
}


def build_media_query(filters: dict[str, str]) -> Select:
    query = select(MediaFile)
    joins_needed: set[type] = set()
    conditions = []

    tz_offset_minutes = _safe_int(filters["tz_offset"], "tz_offset") if filters.get("tz_offset") else 0

    if "library_id" in filters and filters["library_id"]:
        query = query.join(ScannedFolder).join(
            library_folders,
            library_folders.c.folder_id == ScannedFolder.id,
        )
        conditions.append(library_folders.c.library_id == _safe_int(filters["library_id"], "library_id"))

    if "folder_id" in filters and filters["folder_id"]:
        conditions.append(MediaFile.folder_id == _safe_int(filters["folder_id"], "folder_id"))

    for param, value in filters.items():
        if param not in FILTER_REGISTRY or not value:
            continue

        model, column_name, filter_type = FILTER_REGISTRY[param]
        col = getattr(model, column_name)

        if filter_type in ("count_gte", "count_lte"):
            count_subq = (
                select(func.count())
                .where(model.media_file_id == MediaFile.id)
                .correlate(MediaFile)
                .scalar_subquery()
            )
            if filter_type == "count_gte":
                conditions.append(count_subq >= _safe_int(value, param))
            else:
                conditions.append(count_subq <= _safe_int(value, param))
            continue

        if filter_type == "enum":
            inverted = value.startswith("!")
            raw = value[1:] if inverted else value
            values = [v.strip() for v in raw.split(",")]
            has_none = "(none)" in values
            values = [v for v in values if v != "(none)"]
            if values and isinstance(col.type, Integer):
                values = [_safe_int(v, param) for v in values]
            if inverted:
                if model == MediaFile:
                    parts = []
                    if values:
                        parts.append(col.notin_(values))
                    if has_none:
                        parts.append(col.isnot(None))
                    if parts:
                        conditions.append(and_(*parts))
                else:
                    match_parts = []
                    if values:
                        match_parts.append(col.in_(values))
                    if has_none:
                        match_parts.append(col.is_(None))
                    subq = select(model.media_file_id).where(
                        model.media_file_id == MediaFile.id,
                        or_(*match_parts) if len(match_parts) > 1 else match_parts[0],
                    )
                    conditions.append(not_(exists(subq)))
            else:
                if model != MediaFile:
                    joins_needed.add(model)
                if has_none and values:
                    conditions.append(or_(col.in_(values), col.is_(None)))
                elif has_none:
                    conditions.append(col.is_(None))
                else:
                    conditions.append(col.in_(values))
        else:
            if model != MediaFile:
                joins_needed.add(model)
            if filter_type == "boolean":
                conditions.append(col == (value.lower() in ("true", "1", "yes")))
            elif filter_type == "gte":
                conditions.append(col >= _safe_int(value, param))
            elif filter_type == "lte":
                conditions.append(col <= _safe_int(value, param))
            elif filter_type == "date_gte":
                conditions.append(col >= _safe_date(value, param, tz_offset_minutes))
            elif filter_type == "date_lte":
                dt = _safe_date(value, param, tz_offset_minutes)
                conditions.append(col < dt + timedelta(days=1))
            elif filter_type == "text":
                escaped = _escape_like(value)
                conditions.append(col.ilike(f"%{escaped}%", escape="\\"))
            elif filter_type == "prefix":
                escaped = _escape_like(value)
                conditions.append(col.like(f"{escaped}%", escape="\\"))
            elif filter_type == "fuzzy":
                tokens = [t for t in re.split(r"[\s._\-]+", value) if t]
                if tokens:
                    token_conditions = [
                        col.ilike(f"%{_escape_like(t)}%", escape="\\")
                        for t in tokens
                    ]
                    conditions.append(and_(*token_conditions))

    for model in joins_needed:
        query = query.join(model)

    if conditions:
        query = query.where(and_(*conditions))

    return query.distinct()


async def get_filter_options(
    db: AsyncSession, *, library_id: int | None = None
) -> dict[str, list[str]]:
    options = {}

    # Group enum filters by model to reduce query count
    model_filters: dict[type, list[tuple[str, str]]] = {}
    for param, (model, column_name, filter_type) in FILTER_REGISTRY.items():
        if filter_type != "enum":
            continue
        model_filters.setdefault(model, []).append((param, column_name))

    for model, filters in model_filters.items():
        for param, column_name in filters:
            col = getattr(model, column_name)
            query = select(col).where(col.isnot(None))
            if library_id:
                if model == MediaFile:
                    query = query.join(ScannedFolder).join(
                        library_folders, library_folders.c.folder_id == ScannedFolder.id
                    )
                else:
                    query = query.join(MediaFile).join(ScannedFolder).join(
                        library_folders, library_folders.c.folder_id == ScannedFolder.id
                    )
                query = query.where(library_folders.c.library_id == library_id)
            result = await db.execute(query.distinct().order_by(col))
            values = [str(r[0]) for r in result.all()]
            if model == MediaFile:
                null_query = select(func.count()).select_from(MediaFile).where(col.is_(None))
                if library_id:
                    null_query = null_query.join(ScannedFolder).join(
                        library_folders, library_folders.c.folder_id == ScannedFolder.id
                    ).where(library_folders.c.library_id == library_id)
            else:
                null_query = select(func.count()).select_from(model).where(col.is_(None))
                if library_id:
                    null_query = null_query.join(MediaFile).join(ScannedFolder).join(
                        library_folders, library_folders.c.folder_id == ScannedFolder.id
                    ).where(library_folders.c.library_id == library_id)
            null_count = (await db.execute(null_query)).scalar()
            if null_count:
                values.insert(0, "(none)")
            if values:
                options[param] = values

    return options
