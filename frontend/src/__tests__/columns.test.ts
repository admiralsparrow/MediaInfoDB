import { describe, it, expect } from "vitest";
import {
  formatBitrate,
  formatAudioTrack,
  orderByGroup,
  ALL_COLUMNS,
  DEFAULT_COLUMN_KEYS,
  COLUMN_GROUPS,
  type ColumnDef,
} from "../components/MediaTable/columns";
import type { MediaFileDetail, AudioTrack, VideoTrack } from "../types/media";

// ── Helper to build minimal MediaFileDetail objects ────────────────

function makeMedia(overrides: Partial<MediaFileDetail> = {}): MediaFileDetail {
  return {
    id: 1,
    file_path: "/media/movie.mkv",
    file_name: "movie.mkv",
    relative_path: null,
    file_size_bytes: null,
    container_format: null,
    title: null,
    overall_bitrate: null,
    duration_ms: null,
    release_group: null,
    source: null,
    provider: null,
    year: null,
    stream_count: null,
    hybrid: false,
    scanned_at: "2024-01-01T00:00:00Z",
    file_modified_at: null,
    video_tracks: [],
    audio_tracks: [],
    subtitle_tracks: [],
    ...overrides,
  };
}

function makeVideoTrack(overrides: Partial<VideoTrack> = {}): VideoTrack {
  return {
    id: 1, track_index: 0, codec: null, bitrate: null, width: null, height: null,
    framerate: null, hdr10: false, dolby_vision: false, dv_layer: null, dv_profile: null,
    hdr10_plus: false, language: null, track_name: null, is_default: false, is_forced: false,
    display_aspect_ratio: null, bit_depth: null, color_primaries: null,
    transfer_characteristics: null, encoding_library: null, scan_type: null,
    chroma_subsampling: null, resolution: null,
    ...overrides,
  };
}

function makeAudioTrack(overrides: Partial<AudioTrack> = {}): AudioTrack {
  return {
    id: 1, track_index: 0, codec: null, bitrate: null, channel_layout: null,
    channels: null, language: null, track_name: null, is_default: false,
    is_original: false, is_forced: false, is_commentary: false, is_atmos: false,
    sample_rate: null, compression_mode: null,
    ...overrides,
  };
}

// ── formatBitrate ──────────────────────────────────────────────────

describe("formatBitrate", () => {
  it("returns dash for null", () => {
    expect(formatBitrate(null)).toBe("-");
  });

  it("returns dash for zero", () => {
    expect(formatBitrate(0)).toBe("-");
  });

  it("formats megabits", () => {
    expect(formatBitrate(5_000_000)).toBe("5.0 Mbps");
    expect(formatBitrate(12_500_000)).toBe("12.5 Mbps");
  });

  it("formats kilobits", () => {
    expect(formatBitrate(128_000)).toBe("128 kbps");
    expect(formatBitrate(1_000)).toBe("1 kbps");
  });

  it("formats bits", () => {
    expect(formatBitrate(500)).toBe("500 bps");
  });

  it("formats edge case at 1 Mbps boundary", () => {
    expect(formatBitrate(1_000_000)).toBe("1.0 Mbps");
    expect(formatBitrate(999_999)).toBe("1000 kbps");
  });
});

// ── formatAudioTrack ───────────────────────────────────────────────

describe("formatAudioTrack", () => {
  it("formats basic audio track", () => {
    const track = makeAudioTrack({ language: "en", codec: "AAC", channel_layout: "2.0" });
    expect(formatAudioTrack(track)).toBe("EN AAC 2.0");
  });

  it("includes Atmos flag", () => {
    const track = makeAudioTrack({ language: "en", codec: "TrueHD", channel_layout: "7.1", is_atmos: true });
    expect(formatAudioTrack(track)).toContain("Atmos");
  });

  it("includes Commentary flag", () => {
    const track = makeAudioTrack({ language: "en", codec: "AAC", is_commentary: true });
    expect(formatAudioTrack(track)).toContain("[Commentary]");
  });

  it("includes custom track name", () => {
    const track = makeAudioTrack({ language: "en", codec: "AAC", track_name: "Director's Mix" });
    expect(formatAudioTrack(track)).toContain('"Director\'s Mix"');
  });

  it("omits generic language track name", () => {
    const track = makeAudioTrack({ language: "en", codec: "AAC", track_name: "English" });
    expect(formatAudioTrack(track)).not.toContain('"English"');
  });

  it("handles empty track", () => {
    const track = makeAudioTrack();
    expect(formatAudioTrack(track)).toBe("");
  });
});

// ── orderByGroup ───────────────────────────────────────────────────

describe("orderByGroup", () => {
  it("orders keys by group", () => {
    const keys = ["video_codec", "filename", "audio", "container"];
    const ordered = orderByGroup(keys);
    expect(ordered.indexOf("filename")).toBeLessThan(ordered.indexOf("container"));
    expect(ordered.indexOf("container")).toBeLessThan(ordered.indexOf("video_codec"));
    expect(ordered.indexOf("video_codec")).toBeLessThan(ordered.indexOf("audio"));
  });

  it("preserves within-group order from ALL_COLUMNS", () => {
    const keys = ["overall_bitrate", "container", "title"];
    const ordered = orderByGroup(keys);
    expect(ordered).toEqual(["title", "container", "overall_bitrate"]);
  });

  it("drops keys not in ALL_COLUMNS", () => {
    const keys = ["filename", "nonexistent"];
    const ordered = orderByGroup(keys);
    expect(ordered).toEqual(["filename"]);
  });

  it("returns empty for empty input", () => {
    expect(orderByGroup([])).toEqual([]);
  });
});

// ── ALL_COLUMNS structure ──────────────────────────────────────────

describe("ALL_COLUMNS", () => {
  it("has unique keys", () => {
    const keys = ALL_COLUMNS.map((c) => c.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("every column has a valid group", () => {
    const validGroups = COLUMN_GROUPS.map((g) => g.key);
    for (const col of ALL_COLUMNS) {
      expect(validGroups).toContain(col.group);
    }
  });

  it("every default column exists in ALL_COLUMNS", () => {
    const allKeys = ALL_COLUMNS.map((c) => c.key);
    for (const key of DEFAULT_COLUMN_KEYS) {
      expect(allKeys).toContain(key);
    }
  });

  it("every getValue returns a string", () => {
    const media = makeMedia({
      file_name: "test.mkv",
      container_format: "Matroska",
      overall_bitrate: 5_000_000,
      duration_ms: 7200000,
      file_size_bytes: 4_000_000_000,
      video_tracks: [makeVideoTrack({ codec: "HEVC", width: 3840, height: 2160 })],
      audio_tracks: [makeAudioTrack({ codec: "AAC", language: "en", channel_layout: "2.0" })],
      subtitle_tracks: [{ id: 1, track_index: 0, codec: "SRT", language: "en", track_name: null, is_default: true, is_forced: false, is_hearing_impaired: false }],
    });
    for (const col of ALL_COLUMNS) {
      const val = col.getValue(media);
      expect(typeof val).toBe("string");
    }
  });

  it("getValue handles empty media gracefully", () => {
    const empty = makeMedia();
    for (const col of ALL_COLUMNS) {
      expect(() => col.getValue(empty)).not.toThrow();
    }
  });
});

// ── Column getValue specific tests ─────────────────────────────────

describe("column getValue formatters", () => {
  function getCol(key: string): ColumnDef {
    const col = ALL_COLUMNS.find((c) => c.key === key);
    if (!col) throw new Error(`Column ${key} not found`);
    return col;
  }

  it("duration formats hours", () => {
    const media = makeMedia({ duration_ms: 7200000 });
    expect(getCol("duration").getValue(media)).toBe("2:00:00");
  });

  it("duration formats minutes only", () => {
    const media = makeMedia({ duration_ms: 150000 });
    expect(getCol("duration").getValue(media)).toBe("2:30");
  });

  it("duration returns dash for null", () => {
    expect(getCol("duration").getValue(makeMedia())).toBe("-");
  });

  it("file_size formats GB", () => {
    const media = makeMedia({ file_size_bytes: 4_000_000_000 });
    expect(getCol("file_size").getValue(media)).toContain("GB");
  });

  it("file_size formats MB", () => {
    const media = makeMedia({ file_size_bytes: 500_000_000 });
    expect(getCol("file_size").getValue(media)).toContain("MB");
  });

  it("dimensions shows WxH", () => {
    const media = makeMedia({ video_tracks: [makeVideoTrack({ width: 3840, height: 2160 })] });
    expect(getCol("dimensions").getValue(media)).toBe("3840x2160");
  });

  it("dimensions returns dash when missing", () => {
    expect(getCol("dimensions").getValue(makeMedia())).toBe("-");
  });

  it("hdr shows DV + HDR10 combo", () => {
    const media = makeMedia({
      video_tracks: [makeVideoTrack({ dolby_vision: true, dv_profile: 8, dv_layer: "6", hdr10: true })],
    });
    const result = getCol("hdr").getValue(media);
    expect(result).toContain("DV");
    expect(result).toContain("HDR10");
  });

  it("hdr shows SDR when no HDR flags", () => {
    const media = makeMedia({ video_tracks: [makeVideoTrack()] });
    expect(getCol("hdr").getValue(media)).toBe("SDR");
  });

  it("hdr shows HDR10+", () => {
    const media = makeMedia({ video_tracks: [makeVideoTrack({ hdr10_plus: true })] });
    expect(getCol("hdr").getValue(media)).toContain("HDR10+");
  });

  it("bit_depth appends -bit suffix", () => {
    const media = makeMedia({ video_tracks: [makeVideoTrack({ bit_depth: 10 })] });
    expect(getCol("bit_depth").getValue(media)).toBe("10-bit");
  });

  it("audio_sample_rate formats kHz", () => {
    const media = makeMedia({ audio_tracks: [makeAudioTrack({ sample_rate: 48000 })] });
    expect(getCol("audio_sample_rate").getValue(media)).toBe("48.0 kHz");
  });

  it("audio_sample_rate formats Hz", () => {
    const media = makeMedia({ audio_tracks: [makeAudioTrack({ sample_rate: 500 })] });
    expect(getCol("audio_sample_rate").getValue(media)).toBe("500 Hz");
  });

  it("subs lists unique languages", () => {
    const media = makeMedia({
      subtitle_tracks: [
        { id: 1, track_index: 0, codec: "SRT", language: "en", track_name: null, is_default: true, is_forced: false, is_hearing_impaired: false },
        { id: 2, track_index: 1, codec: "SRT", language: "en", track_name: "SDH", is_default: false, is_forced: false, is_hearing_impaired: true },
        { id: 3, track_index: 2, codec: "SRT", language: "fr", track_name: null, is_default: false, is_forced: false, is_hearing_impaired: false },
      ],
    });
    expect(getCol("subs").getValue(media)).toBe("en, fr");
  });

  it("hybrid shows Yes/No", () => {
    expect(getCol("hybrid").getValue(makeMedia({ hybrid: true }))).toBe("Yes");
    expect(getCol("hybrid").getValue(makeMedia({ hybrid: false }))).toBe("No");
  });

  it("year shows value or dash", () => {
    expect(getCol("year").getValue(makeMedia({ year: 2024 }))).toBe("2024");
    expect(getCol("year").getValue(makeMedia())).toBe("-");
  });

  it("audio_bitrate shows multiple tracks", () => {
    const media = makeMedia({
      audio_tracks: [
        makeAudioTrack({ bitrate: 5_000_000 }),
        makeAudioTrack({ bitrate: 128_000 }),
        makeAudioTrack({ bitrate: 64_000 }),
      ],
    });
    const result = getCol("audio_bitrate").getValue(media);
    expect(result).toContain("5.0 Mbps");
    expect(result).toContain("128 kbps");
    expect(result).toContain("+1 more");
  });
});
