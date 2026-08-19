export interface MediaFile {
  id: number;
  file_path: string;
  file_name: string;
  relative_path: string | null;
  file_size_bytes: number | null;
  container_format: string | null;
  title: string | null;
  overall_bitrate: number | null;
  duration_ms: number | null;
  release_group: string | null;
  source: string | null;
  provider: string | null;
  year: number | null;
  stream_count: number | null;
  hybrid: boolean;
  scanned_at: string;
  file_modified_at: string | null;
}

export interface VideoTrack {
  id: number;
  track_index: number;
  codec: string | null;
  bitrate: number | null;
  width: number | null;
  height: number | null;
  framerate: number | null;
  hdr10: boolean;
  dolby_vision: boolean;
  dv_layer: string | null;
  dv_profile: number | null;
  hdr10_plus: boolean;
  language: string | null;
  track_name: string | null;
  is_default: boolean;
  is_forced: boolean;
  display_aspect_ratio: string | null;
  bit_depth: number | null;
  color_primaries: string | null;
  transfer_characteristics: string | null;
  encoding_library: string | null;
  scan_type: string | null;
  chroma_subsampling: string | null;
  resolution: string | null;
}

export interface AudioTrack {
  id: number;
  track_index: number;
  codec: string | null;
  bitrate: number | null;
  channel_layout: string | null;
  channels: number | null;
  language: string | null;
  track_name: string | null;
  is_default: boolean;
  is_original: boolean;
  is_forced: boolean;
  is_commentary: boolean;
  is_atmos: boolean;
  sample_rate: number | null;
  compression_mode: string | null;
}

export interface SubtitleTrack {
  id: number;
  track_index: number;
  codec: string | null;
  language: string | null;
  track_name: string | null;
  is_default: boolean;
  is_forced: boolean;
  is_hearing_impaired: boolean;
}

export interface MediaFileDetail extends MediaFile {
  video_tracks: VideoTrack[];
  audio_tracks: AudioTrack[];
  subtitle_tracks: SubtitleTrack[];
}
