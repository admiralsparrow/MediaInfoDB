import type { MediaFileDetail, AudioTrack } from "../../types/media";

export type GroupKey = "file" | "general" | "video" | "audio" | "subtitle";

export interface ColumnDef {
  key: string;
  label: string;
  group: GroupKey;
  sortField?: string;
  getValue: (file: MediaFileDetail) => string;
}

export const COLUMN_GROUPS: { key: GroupKey; label: string }[] = [
  { key: "file", label: "File" },
  { key: "general", label: "General" },
  { key: "video", label: "Video" },
  { key: "audio", label: "Audio" },
  { key: "subtitle", label: "Subtitles" },
];

const GROUP_ORDER: GroupKey[] = ["file", "general", "video", "audio", "subtitle"];

export const ALL_COLUMNS: ColumnDef[] = [
  // File
  {
    key: "filename",
    label: "Filename",
    group: "file",
    sortField: "file_name",
    getValue: (f) => f.file_name,
  },

  {
    key: "relative_path",
    label: "Path",
    group: "file",
    sortField: "relative_path",
    getValue: (f) => f.relative_path || "-",
  },

  // General
  {
    key: "title",
    label: "Title",
    group: "general",
    sortField: "title",
    getValue: (f) => f.title || "-",
  },
  {
    key: "container",
    label: "Container",
    group: "general",
    sortField: "container_format",
    getValue: (f) => f.container_format || "-",
  },
  {
    key: "overall_bitrate",
    label: "Bitrate",
    group: "general",
    sortField: "overall_bitrate",
    getValue: (f) => formatBitrate(f.overall_bitrate),
  },
  {
    key: "duration",
    label: "Duration",
    group: "general",
    sortField: "duration_ms",
    getValue: (f) => {
      if (!f.duration_ms) return "-";
      const sec = Math.floor(f.duration_ms / 1000);
      const h = Math.floor(sec / 3600);
      const m = Math.floor((sec % 3600) / 60);
      const s = sec % 60;
      if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
      return `${m}:${String(s).padStart(2, "0")}`;
    },
  },
  {
    key: "file_size",
    label: "File Size",
    group: "general",
    sortField: "file_size_bytes",
    getValue: (f) => {
      if (!f.file_size_bytes) return "-";
      const gb = f.file_size_bytes / (1024 * 1024 * 1024);
      if (gb >= 1) return `${gb.toFixed(2)} GB`;
      const mb = f.file_size_bytes / (1024 * 1024);
      return `${mb.toFixed(0)} MB`;
    },
  },

  {
    key: "release_group",
    label: "Release Group",
    group: "general",
    sortField: "release_group",
    getValue: (f) => f.release_group || "-",
  },
  {
    key: "source",
    label: "Source",
    group: "general",
    sortField: "source",
    getValue: (f) => f.source || "-",
  },
  {
    key: "provider",
    label: "Provider",
    group: "general",
    sortField: "provider",
    getValue: (f) => f.provider || "-",
  },
  {
    key: "year",
    label: "Year",
    group: "general",
    sortField: "year",
    getValue: (f) => f.year ? String(f.year) : "-",
  },
  {
    key: "stream_count",
    label: "Streams",
    group: "general",
    sortField: "stream_count",
    getValue: (f) => f.stream_count ? String(f.stream_count) : "-",
  },
  {
    key: "hybrid",
    label: "Hybrid",
    group: "general",
    sortField: "hybrid",
    getValue: (f) => f.hybrid ? "Yes" : "No",
  },
  {
    key: "scanned_at",
    label: "Date Scanned",
    group: "file",
    sortField: "scanned_at",
    getValue: (f) => f.scanned_at ? new Date(f.scanned_at).toLocaleDateString() : "-",
  },
  {
    key: "file_modified_at",
    label: "Date Modified",
    group: "file",
    sortField: "file_modified_at",
    getValue: (f) => f.file_modified_at ? new Date(f.file_modified_at).toLocaleDateString() : "-",
  },

  // Video
  {
    key: "dimensions",
    label: "Dimensions",
    group: "video",
    sortField: "video_width",
    getValue: (f) => {
      const v = f.video_tracks?.[0];
      if (!v?.width || !v?.height) return "-";
      return `${v.width}x${v.height}`;
    },
  },
  {
    key: "resolution",
    label: "Resolution",
    group: "video",
    sortField: "video_resolution",
    getValue: (f) => {
      const v = f.video_tracks?.[0];
      return v?.resolution || "-";
    },
  },
  {
    key: "video_codec",
    label: "Codec",
    group: "video",
    sortField: "video_codec",
    getValue: (f) => f.video_tracks?.[0]?.codec || "-",
  },
  {
    key: "hdr",
    label: "HDR",
    group: "video",
    getValue: (f) => {
      const v = f.video_tracks?.[0];
      if (!v) return "-";
      const parts: string[] = [];
      if (v.dolby_vision) parts.push(`DV P${v.dv_profile ?? "?"}.L${v.dv_layer ? parseInt(v.dv_layer, 10) : "?"}`);
      if (v.hdr10) parts.push("HDR10");
      if (v.hdr10_plus) parts.push("HDR10+");
      return parts.length ? parts.join(" / ") : "SDR";
    },
  },
  {
    key: "video_bitrate",
    label: "Bitrate",
    group: "video",
    sortField: "video_bitrate",
    getValue: (f) => formatBitrate(f.video_tracks?.[0]?.bitrate ?? null),
  },
  {
    key: "framerate",
    label: "FPS",
    group: "video",
    sortField: "video_framerate",
    getValue: (f) => {
      const fps = f.video_tracks?.[0]?.framerate;
      return fps ? `${fps}` : "-";
    },
  },
  {
    key: "video_name",
    label: "Track Name",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.track_name || "-",
  },
  {
    key: "video_default",
    label: "Default",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.is_default ? "Yes" : "No",
  },
  {
    key: "aspect_ratio",
    label: "OAR",
    group: "video",
    sortField: "video_aspect_ratio",
    getValue: (f) => f.video_tracks?.[0]?.display_aspect_ratio || "-",
  },
  {
    key: "bit_depth",
    label: "Bit Depth",
    group: "video",
    sortField: "video_bit_depth",
    getValue: (f) => {
      const bd = f.video_tracks?.[0]?.bit_depth;
      return bd ? `${bd}-bit` : "-";
    },
  },
  {
    key: "color_primaries",
    label: "Color Primaries",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.color_primaries || "-",
  },
  {
    key: "transfer_characteristics",
    label: "Transfer",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.transfer_characteristics || "-",
  },
  {
    key: "encoding_library",
    label: "Encoder",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.encoding_library || "-",
  },
  {
    key: "scan_type",
    label: "Scan Type",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.scan_type || "-",
  },
  {
    key: "chroma_subsampling",
    label: "Chroma",
    group: "video",
    getValue: (f) => f.video_tracks?.[0]?.chroma_subsampling || "-",
  },

  // Audio
  {
    key: "audio",
    label: "Audio",
    group: "audio",
    getValue: (f) => formatAudioSummary(f.audio_tracks),
  },
  {
    key: "audio_bitrate",
    label: "Bitrate",
    group: "audio",
    sortField: "audio_bitrate",
    getValue: (f) => {
      if (!f.audio_tracks?.length) return "-";
      const shown = f.audio_tracks.slice(0, 2).map(t => formatBitrate(t.bitrate ?? null));
      const remaining = f.audio_tracks.length - 2;
      if (remaining > 0) shown.push(`+${remaining} more`);
      return shown.join("\n");
    },
  },
  {
    key: "audio_default",
    label: "Default",
    group: "audio",
    getValue: (f) => {
      const def = f.audio_tracks?.find((a) => a.is_default);
      return def ? `${def.language || "?"} ${def.channel_layout || ""}`.trim() : "-";
    },
  },
  {
    key: "audio_name",
    label: "Track Name",
    group: "audio",
    getValue: (f) => {
      const names = f.audio_tracks
        ?.map((t) => getDisplayName(t.track_name, t.language))
        .filter(Boolean);
      if (!names?.length) return "-";
      const joined = names.join(", ");
      return joined.length > 30 ? joined.slice(0, 30) + "…" : joined;
    },
  },
  {
    key: "audio_language",
    label: "Languages",
    group: "audio",
    getValue: (f) => {
      const langs = [...new Set(f.audio_tracks?.map((a) => a.language).filter(Boolean))];
      return langs.join(", ") || "-";
    },
  },
  {
    key: "audio_sample_rate",
    label: "Sample Rate",
    group: "audio",
    sortField: "audio_sample_rate",
    getValue: (f) => {
      const sr = f.audio_tracks?.[0]?.sample_rate;
      if (!sr) return "-";
      return sr >= 1000 ? `${(sr / 1000).toFixed(1)} kHz` : `${sr} Hz`;
    },
  },
  {
    key: "audio_compression",
    label: "Compression",
    group: "audio",
    getValue: (f) => f.audio_tracks?.[0]?.compression_mode || "-",
  },

  // Subtitle
  {
    key: "subs",
    label: "Subtitles",
    group: "subtitle",
    getValue: (f) => {
      const subs = f.subtitle_tracks;
      if (!subs?.length) return "-";
      const langs = [...new Set(subs.map((s) => s.language).filter(Boolean))];
      return langs.join(", ") || `${subs.length} tracks`;
    },
  },
  {
    key: "sub_names",
    label: "Track Names",
    group: "subtitle",
    getValue: (f) => {
      const names = f.subtitle_tracks
        ?.map((s) => getDisplayName(s.track_name, s.language))
        .filter(Boolean);
      return names?.length ? names.join(", ") : "-";
    },
  },
];

export const DEFAULT_COLUMN_KEYS = [
  "filename",
  "container",
  "overall_bitrate",
  "dimensions",
  "resolution",
  "video_codec",
  "hdr",
  "audio",
  "subs",
];

/**
 * Given a set of visible column keys, return them ordered by group.
 * Columns within the same group maintain their relative order from ALL_COLUMNS.
 */
export function orderByGroup(keys: string[]): string[] {
  const result: string[] = [];
  for (const group of GROUP_ORDER) {
    const groupCols = ALL_COLUMNS.filter((c) => c.group === group);
    for (const col of groupCols) {
      if (keys.includes(col.key)) {
        result.push(col.key);
      }
    }
  }
  return result;
}

export function formatBitrate(bps: number | null): string {
  if (!bps) return "-";
  if (bps >= 1_000_000) return `${(bps / 1_000_000).toFixed(1)} Mbps`;
  if (bps >= 1_000) return `${(bps / 1_000).toFixed(0)} kbps`;
  return `${bps} bps`;
}

export function formatAudioTrack(track: AudioTrack): string {
  const parts: string[] = [];
  if (track.language) parts.push(track.language.toUpperCase());
  if (track.codec) parts.push(track.codec);
  if (track.channel_layout) parts.push(track.channel_layout);
  if (track.is_atmos) parts.push("Atmos");
  if (track.is_commentary) parts.push("[Commentary]");
  const name = getDisplayName(track.track_name, track.language);
  if (name) parts.push(`"${name}"`);
  return parts.join(" ");
}

function formatAudioSummary(tracks: AudioTrack[] | undefined): string {
  if (!tracks?.length) return "-";
  return tracks.map(formatAudioTrack).join("\n");
}

function getDisplayName(trackName: string | null | undefined, language: string | null | undefined): string | null {
  if (!trackName) return null;
  const langNames = ["english", "french", "spanish", "german", "italian", "japanese", "korean", "chinese", "portuguese", "russian", "dutch", "arabic", "hindi"];
  if (langNames.includes(trackName.toLowerCase())) return null;
  if (language && trackName.toLowerCase() === language.toLowerCase()) return null;
  return trackName;
}
