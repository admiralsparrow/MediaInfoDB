import logging
import os
import re
from pathlib import Path

from pymediainfo import MediaInfo

from app.models.audio_track import AudioTrack
from app.models.media_file import MediaFile
from app.models.subtitle_track import SubtitleTrack
from app.models.video_track import VideoTrack

logger = logging.getLogger(__name__)

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".m2ts", ".vob", ".3gp",
}


def find_video_files(folder_path: str) -> list[str]:
    video_files = []
    for root, _dirs, files in os.walk(folder_path):
        for f in files:
            if Path(f).suffix.lower() in VIDEO_EXTENSIONS:
                video_files.append(os.path.join(root, f))
    return sorted(video_files)


def scan_file(file_path: str) -> MediaFile | None:
    try:
        info = MediaInfo.parse(file_path)
    except Exception as e:
        logger.error("Failed to parse %s: %s", file_path, e)
        return None

    filename = os.path.basename(file_path)
    media_file = MediaFile(
        file_path=file_path,
        file_name=filename,
        file_size_bytes=os.path.getsize(file_path),
        release_group=_parse_release_group(filename),
        source=_parse_source(filename),
        provider=_parse_provider(filename),
        year=_parse_year(filename, file_path),
        hybrid=_parse_hybrid(filename, file_path),
    )

    for track in info.tracks:
        if track.track_type == "General":
            media_file.container_format = track.format
            media_file.title = track.title
            media_file.overall_bitrate = _get_bitrate(track, overall=True)
            media_file.duration_ms = _int_or_none(track.duration)

        elif track.track_type == "Video":
            video = VideoTrack(
                track_index=_track_index(track),
                codec=track.format,
                bitrate=_get_bitrate(track),
                width=_int_or_none(track.width),
                height=_int_or_none(track.height),
                framerate=_float_or_none(track.frame_rate),
                hdr10=_detect_hdr10(track),
                dolby_vision=_detect_dolby_vision(track),
                dv_layer=_get_dv_layer(track),
                dv_profile=_get_dv_profile(track),
                hdr10_plus=_detect_hdr10_plus(track),
                language=track.language,
                track_name=track.title,
                is_default=_is_yes(track.default),
                is_forced=_is_yes(track.forced),
                display_aspect_ratio=_format_aspect_ratio(getattr(track, "display_aspect_ratio", None)),
                bit_depth=_int_or_none(getattr(track, "bit_depth", None)),
                color_primaries=getattr(track, "color_primaries", None),
                transfer_characteristics=getattr(track, "transfer_characteristics", None),
                encoding_library=_get_encoding_library(track),
                scan_type=getattr(track, "scan_type", None),
                chroma_subsampling=getattr(track, "chroma_subsampling", None),
                resolution=_compute_resolution(
                    _int_or_none(getattr(track, "height", None)),
                    _int_or_none(getattr(track, "width", None)),
                ),
            )
            media_file.video_tracks.append(video)

        elif track.track_type == "Audio":
            audio = AudioTrack(
                track_index=_track_index(track),
                codec=track.format,
                bitrate=_get_bitrate(track),
                channel_layout=_normalize_channel_layout(track),
                channels=_int_or_none(track.channel_s),
                language=track.language,
                track_name=track.title,
                is_default=_is_yes(track.default),
                is_original=_is_yes(getattr(track, "original", None)),
                is_forced=_is_yes(track.forced),
                is_commentary=_detect_commentary(track),
                is_atmos=_detect_atmos(track),
                sample_rate=_int_or_none(getattr(track, "sampling_rate", None)),
                compression_mode=getattr(track, "compression_mode", None),
            )
            media_file.audio_tracks.append(audio)

        elif track.track_type == "Text":
            subtitle = SubtitleTrack(
                track_index=_track_index(track),
                codec=track.format,
                language=track.language,
                track_name=track.title,
                is_default=_is_yes(track.default),
                is_forced=_is_yes(track.forced),
                is_hearing_impaired=_detect_hearing_impaired(track),
            )
            media_file.subtitle_tracks.append(subtitle)

    # Fallback: calculate overall bitrate from file size and duration
    if not media_file.overall_bitrate and media_file.duration_ms and media_file.file_size_bytes:
        media_file.overall_bitrate = int(
            (media_file.file_size_bytes * 8) / (media_file.duration_ms / 1000)
        )

    media_file.stream_count = (
        len(media_file.video_tracks) + len(media_file.audio_tracks) + len(media_file.subtitle_tracks)
    )

    return media_file


def _get_bitrate(track, overall: bool = False) -> int | None:
    if overall:
        val = _int_or_none(track.overall_bit_rate)
        if val:
            return val
    val = _int_or_none(track.bit_rate)
    if val:
        return val
    val = _int_or_none(getattr(track, "nominal_bit_rate", None))
    if val:
        return val
    val = _int_or_none(getattr(track, "maximum_bit_rate", None))
    if val:
        return val
    # Calculate from stream size and duration
    stream_size = _int_or_none(getattr(track, "stream_size", None))
    duration = _float_or_none(getattr(track, "duration", None))
    if stream_size and duration and duration > 0:
        return int((stream_size * 8) / (duration / 1000))
    return None


def _track_index(track) -> int:
    return int(track.stream_identifier or track.streamorder or 0)


def _int_or_none(val) -> int | None:
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


def _float_or_none(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _is_yes(val) -> bool:
    if val is None:
        return False
    return str(val).lower() in ("yes", "true", "1")


def _detect_hdr10(track) -> bool:
    hdr_format = getattr(track, "hdr_format", "") or ""
    transfer = getattr(track, "transfer_characteristics", "") or ""
    return "HDR10" in hdr_format or "PQ" in transfer.upper()


def _detect_dolby_vision(track) -> bool:
    hdr_format = getattr(track, "hdr_format", "") or ""
    return "Dolby Vision" in hdr_format


def _get_dv_layer(track) -> str | None:
    import re
    level_str = getattr(track, "hdr_format_level", "") or ""
    match = re.search(r"(\d+)", level_str)
    if match:
        return str(int(match.group(1)))
    return None


def _get_dv_profile(track) -> int | None:
    import re
    profile_str = getattr(track, "hdr_format_profile", "") or ""
    match = re.search(r"dvhe?\.0?(\d+)", profile_str.lower())
    if match:
        return int(match.group(1))
    hdr_format = getattr(track, "hdr_format", "") or ""
    match = re.search(r"dvhe?\.0?(\d+)", hdr_format.lower())
    if match:
        return int(match.group(1))
    profile_match = re.search(r"profile\s*(\d+)", hdr_format.lower())
    if profile_match:
        return int(profile_match.group(1))
    return None


def _detect_hdr10_plus(track) -> bool:
    hdr_format = getattr(track, "hdr_format", "") or ""
    hdr_format_compatibility = getattr(track, "hdr_format_compatibility", "") or ""
    return "HDR10+" in hdr_format or "HDR10+" in hdr_format_compatibility


def _normalize_channel_layout(track) -> str | None:
    channels = _int_or_none(track.channel_s)
    if channels is None:
        return None

    layout_str = (track.channel_layout or "").upper()
    lfe_count = layout_str.count("LFE")

    # Check for height/overhead channels (Atmos object beds)
    overhead = 0
    for token in layout_str.replace("/", " ").split():
        if token.startswith("T") or token.startswith("VH") or "HEIGHT" in token:
            overhead += 1

    if overhead > 0:
        bed = channels - lfe_count - overhead
        return f"{bed}.{lfe_count}.{overhead}"

    if lfe_count > 0:
        main = channels - lfe_count
        return f"{main}.{lfe_count}"

    # Fallback based on channel count
    KNOWN = {1: "1.0", 2: "2.0", 6: "5.1", 8: "7.1"}
    return KNOWN.get(channels, f"{channels}.0")


def _detect_atmos(track) -> bool:
    commercial = getattr(track, "format_commercial_name", "") or ""
    if "atmos" in commercial.lower():
        return True
    title = (track.title or "").lower()
    if "atmos" in title:
        return True
    # E-AC-3 with JOC (Joint Object Coding) = Atmos
    additional = getattr(track, "format_additionalfeatures", "") or ""
    if "JOC" in additional.upper():
        return True
    return False


def _detect_commentary(track) -> bool:
    title = (track.title or "").lower()
    return "commentary" in title or "comment" in title


_HI_PATTERN = re.compile(r"\b(?:sdh|hearing impaired|hi)\b", re.IGNORECASE)


def _detect_hearing_impaired(track) -> bool:
    title = track.title or ""
    return _HI_PATTERN.search(title) is not None


def _parse_release_group(filename: str) -> str | None:
    stem = Path(filename).stem
    match = re.search(r"-\s?([A-Za-z0-9]+)\)?$", stem)
    return match.group(1) if match else None


_SOURCE_PATTERNS = [
    ("REMUX", re.compile(r"\bREMUX\b", re.IGNORECASE)),
    ("WEB-DL", re.compile(r"\bWEB[-.]?DL\b", re.IGNORECASE)),
    ("WEBRip", re.compile(r"\bWEB[-.]?Rip\b", re.IGNORECASE)),
    ("BluRay", re.compile(r"\bBlu[-.]?Ray\b", re.IGNORECASE)),
    ("BDRip", re.compile(r"\bBDRip\b", re.IGNORECASE)),
    ("DVDRip", re.compile(r"\bDVDRip\b", re.IGNORECASE)),
    ("DVD", re.compile(r"\bDVD\b", re.IGNORECASE)),
    ("HDTV", re.compile(r"\bHDTV\b", re.IGNORECASE)),
]


def _parse_source(filename: str) -> str | None:
    for label, pattern in _SOURCE_PATTERNS:
        if pattern.search(filename):
            return label
    return None


_PROVIDERS = [
    "AMZN", "NF", "ATVP", "DSNP", "HMAX", "MAX", "HULU", "PCOK", "PMTP",
    "iT", "APTV", "STAN", "CR", "CRAV", "BCORE", "VUDU", "MUBI",
]
_PROVIDER_RE = re.compile(
    r"\b(" + "|".join(_PROVIDERS) + r"|MA(?=[\.\-\s]WEB))\b"
)


def _parse_provider(filename: str) -> str | None:
    match = _PROVIDER_RE.search(filename)
    return match.group(1) if match else None


_YEAR_RE = re.compile(r"[\.\s\-\(](\d{4})(?=[\.\s\-\)]|$)")
_RELEASE_INFO_RE = re.compile(
    r"[\.\s\-]("
    r"480[ip]|576[ip]|720[ip]|1080[ip]|2160[ip]|4320[ip]|4K|UHD"
    r"|BluRay|Blu-Ray|BDRip|BRRip|WEB-DL|WEBRip|WEB|HDTV|DVDRip|DVD"
    r"|REMUX|HDR|DV|DoVi|SDR|10bit|HEVC|H\.?264|H\.?265|x264|x265|AVC|MPEG"
    r"|AAC|DTS|TrueHD|Atmos|FLAC|AC3|EAC3|DD[P+]?"
    r")[\.\s\-]",
    re.IGNORECASE,
)


def _parse_year(filename: str, file_path: str) -> int | None:
    for text in (filename, os.path.dirname(file_path)):
        release_start = _RELEASE_INFO_RE.search(text)
        search_region = text[: release_start.start()] if release_start else text
        candidates = [
            int(m.group(1))
            for m in _YEAR_RE.finditer(search_region)
            if 1900 <= int(m.group(1)) <= 2099
        ]
        if candidates:
            return candidates[-1]
    return None


_HYBRID_RE = re.compile(
    r"[\.\s\-\(](\d{4})[\.\s\-\)].*\bHYBRID\b",
    re.IGNORECASE,
)


def _parse_hybrid(filename: str, file_path: str) -> bool:
    for text in (filename, os.path.basename(os.path.dirname(file_path))):
        if _HYBRID_RE.search(text):
            return True
    return False


def _format_aspect_ratio(val) -> str | None:
    if val is None:
        return None
    try:
        ratio = float(val)
        return f"{ratio:.2f}:1"
    except (ValueError, TypeError):
        return str(val) if val else None


def _compute_resolution(height: int | None, width: int | None) -> str | None:
    if height is None and width is None:
        return None
    _TIERS = [
        (4320, 7680, "4320p"),
        (2160, 3840, "2160p"),
        (1080, 1920, "1080p"),
        (720, 1280, "720p"),
        (540, 960, "540p"),
        (480, 854, "480p"),
    ]
    _TOLERANCE = 0.90
    for nominal_h, nominal_w, label in _TIERS:
        if (height and height >= nominal_h * _TOLERANCE) or \
           (width and width >= nominal_w * _TOLERANCE):
            return label
    return "SD"


def _get_encoding_library(track) -> str | None:
    lib = getattr(track, "encoded_library_name", None)
    if lib:
        return str(lib)
    lib = getattr(track, "writing_library", None)
    if lib:
        name = str(lib).split(" ")[0]
        return name
    return None
