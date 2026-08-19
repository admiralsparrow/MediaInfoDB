from datetime import datetime

from pydantic import BaseModel


class VideoTrackResponse(BaseModel):
    id: int
    track_index: int
    codec: str | None
    bitrate: int | None
    width: int | None
    height: int | None
    framerate: float | None
    hdr10: bool
    dolby_vision: bool
    dv_layer: str | None
    dv_profile: int | None
    hdr10_plus: bool
    language: str | None
    track_name: str | None
    is_default: bool
    is_forced: bool
    display_aspect_ratio: str | None
    bit_depth: int | None
    color_primaries: str | None
    transfer_characteristics: str | None
    encoding_library: str | None
    scan_type: str | None
    chroma_subsampling: str | None
    resolution: str | None

    model_config = {"from_attributes": True}


class AudioTrackResponse(BaseModel):
    id: int
    track_index: int
    codec: str | None
    bitrate: int | None
    channel_layout: str | None
    channels: int | None
    language: str | None
    track_name: str | None
    is_default: bool
    is_original: bool
    is_forced: bool
    is_commentary: bool
    is_atmos: bool
    sample_rate: int | None
    compression_mode: str | None

    model_config = {"from_attributes": True}


class SubtitleTrackResponse(BaseModel):
    id: int
    track_index: int
    codec: str | None
    language: str | None
    track_name: str | None
    is_default: bool
    is_forced: bool
    is_hearing_impaired: bool

    model_config = {"from_attributes": True}


class MediaFileResponse(BaseModel):
    id: int
    file_path: str
    file_name: str
    relative_path: str | None
    file_size_bytes: int | None
    container_format: str | None
    title: str | None
    overall_bitrate: int | None
    duration_ms: int | None
    release_group: str | None
    source: str | None
    provider: str | None
    year: int | None
    stream_count: int | None
    hybrid: bool
    scanned_at: datetime
    file_modified_at: datetime | None

    model_config = {"from_attributes": True}


class MediaFileDetailResponse(MediaFileResponse):
    video_tracks: list[VideoTrackResponse]
    audio_tracks: list[AudioTrackResponse]
    subtitle_tracks: list[SubtitleTrackResponse]
