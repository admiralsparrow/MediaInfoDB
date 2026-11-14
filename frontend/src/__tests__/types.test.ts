/**
 * Cross-stack consistency tests: verify that frontend filter definitions
 * and column definitions reference API parameters that the backend knows about.
 */

import { describe, it, expect } from "vitest";
import { filterDefinitions } from "../components/Filters/filterDefinitions";
import { ALL_COLUMNS, COLUMN_GROUPS } from "../components/MediaTable/columns";

// These are the backend's recognized filter params (from FILTER_REGISTRY + special params).
// Kept as a set here so we catch frontend/backend drift.
const BACKEND_FILTER_PARAMS = new Set([
  "search", "folder_path", "container_format", "title",
  "overall_bitrate_min", "overall_bitrate_max",
  "release_group", "source", "provider", "year", "hybrid",
  "video.codec", "video.bitrate_min", "video.bitrate_max",
  "video.width_min", "video.width_max", "video.height_min", "video.height_max",
  "video.resolution", "video.hdr10", "video.dolby_vision",
  "video.dv_profile", "video.dv_layer", "video.hdr10_plus",
  "video.language", "video.is_default", "video.is_forced",
  "video.display_aspect_ratio", "video.bit_depth", "video.color_primaries",
  "video.transfer_characteristics", "video.encoding_library",
  "video.scan_type", "video.chroma_subsampling",
  "audio.codec", "audio.bitrate_min", "audio.bitrate_max",
  "audio.channel_layout", "audio.language",
  "audio.is_default", "audio.is_original", "audio.is_forced",
  "audio.is_commentary", "audio.is_atmos",
  "audio.sample_rate", "audio.compression_mode",
  "audio.track_count_min", "audio.track_count_max",
  "subtitle.codec", "subtitle.language",
  "subtitle.is_default", "subtitle.is_forced", "subtitle.is_hearing_impaired",
  "subtitle.track_count_min", "subtitle.track_count_max",
  "scanned_at_min", "scanned_at_max",
  "file_modified_at_min", "file_modified_at_max",
  // Special params not in FILTER_REGISTRY
  "library_id", "folder_id", "tz_offset", "invalid",
]);

const BACKEND_SORT_FIELDS = new Set([
  "file_name", "title", "container_format", "overall_bitrate",
  "duration_ms", "file_size_bytes", "relative_path",
  "release_group", "source", "provider",
  "scanned_at", "file_modified_at",
  "video_codec", "video_bitrate", "video_width", "video_height", "video_framerate",
  "audio_codec", "audio_bitrate", "audio_channels", "audio_sample_rate",
  "year", "stream_count", "hybrid",
  "video_bit_depth", "video_aspect_ratio", "video_resolution",
]);

describe("frontend-backend filter consistency", () => {
  it("all frontend filter apiParams exist in the backend registry", () => {
    for (const def of filterDefinitions) {
      expect(BACKEND_FILTER_PARAMS).toContain(def.apiParam);
      if (def.apiParamMax) {
        expect(BACKEND_FILTER_PARAMS).toContain(def.apiParamMax);
      }
    }
  });
});

describe("frontend-backend sort consistency", () => {
  it("all column sortFields exist in the backend SORT_MAP", () => {
    for (const col of ALL_COLUMNS) {
      if (col.sortField) {
        expect(BACKEND_SORT_FIELDS).toContain(col.sortField);
      }
    }
  });
});

describe("column/group integrity", () => {
  it("COLUMN_GROUPS has all groups referenced by columns", () => {
    const groupKeys = new Set(COLUMN_GROUPS.map((g) => g.key));
    for (const col of ALL_COLUMNS) {
      expect(groupKeys).toContain(col.group);
    }
  });

  it("every group has at least one column", () => {
    for (const group of COLUMN_GROUPS) {
      const count = ALL_COLUMNS.filter((c) => c.group === group.key).length;
      expect(count).toBeGreaterThan(0);
    }
  });
});
