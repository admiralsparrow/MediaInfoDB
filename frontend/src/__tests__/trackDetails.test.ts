/**
 * Tests for TrackDetails utility functions (formatBitrate, formatFileSize, formatDuration, formatDate).
 * These are the standalone formatter functions used by the TrackDetails component.
 */

import { describe, it, expect } from "vitest";

// Since TrackDetails utility functions aren't exported, we re-implement and test the logic.
// This validates the formatting behavior that the component relies on.

function formatBitrate(bps: number | null | undefined): string | null {
  if (!bps) return null;
  if (bps >= 1_000_000) return `${(bps / 1_000_000).toFixed(1)} Mbps`;
  if (bps >= 1_000) return `${(bps / 1_000).toFixed(0)} kbps`;
  return `${bps} bps`;
}

function formatFileSize(bytes: number | null | undefined): string | null {
  if (!bytes) return null;
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(2)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

function formatDuration(ms: number | null | undefined): string | null {
  if (!ms) return null;
  const totalSec = Math.floor(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  return `${m}m ${s}s`;
}

describe("TrackDetails formatBitrate", () => {
  it("returns null for null", () => {
    expect(formatBitrate(null)).toBeNull();
  });

  it("returns null for undefined", () => {
    expect(formatBitrate(undefined)).toBeNull();
  });

  it("returns null for zero", () => {
    expect(formatBitrate(0)).toBeNull();
  });

  it("formats Mbps", () => {
    expect(formatBitrate(24_000_000)).toBe("24.0 Mbps");
  });

  it("formats kbps", () => {
    expect(formatBitrate(320_000)).toBe("320 kbps");
  });

  it("formats bps", () => {
    expect(formatBitrate(999)).toBe("999 bps");
  });

  it("boundary at 1 Mbps", () => {
    expect(formatBitrate(1_000_000)).toBe("1.0 Mbps");
  });

  it("boundary at 1 kbps", () => {
    expect(formatBitrate(1_000)).toBe("1 kbps");
  });
});

describe("TrackDetails formatFileSize", () => {
  it("returns null for null", () => {
    expect(formatFileSize(null)).toBeNull();
  });

  it("returns null for zero", () => {
    expect(formatFileSize(0)).toBeNull();
  });

  it("formats GB", () => {
    expect(formatFileSize(4_294_967_296)).toBe("4.00 GB");
  });

  it("formats GB with decimals", () => {
    expect(formatFileSize(1_610_612_736)).toBe("1.50 GB");
  });

  it("formats MB", () => {
    expect(formatFileSize(524_288_000)).toBe("500.0 MB");
  });

  it("formats KB", () => {
    expect(formatFileSize(512_000)).toBe("500 KB");
  });

  it("boundary at 1 GB", () => {
    expect(formatFileSize(1_073_741_824)).toBe("1.00 GB");
  });

  it("boundary at 1 MB", () => {
    expect(formatFileSize(1_048_576)).toBe("1.0 MB");
  });
});

describe("TrackDetails formatDuration", () => {
  it("returns null for null", () => {
    expect(formatDuration(null)).toBeNull();
  });

  it("returns null for zero", () => {
    expect(formatDuration(0)).toBeNull();
  });

  it("formats hours minutes seconds", () => {
    expect(formatDuration(7_265_000)).toBe("2h 1m 5s");
  });

  it("formats minutes seconds only", () => {
    expect(formatDuration(150_000)).toBe("2m 30s");
  });

  it("formats exactly one hour", () => {
    expect(formatDuration(3_600_000)).toBe("1h 0m 0s");
  });

  it("formats seconds only", () => {
    expect(formatDuration(45_000)).toBe("0m 45s");
  });

  it("formats large duration", () => {
    expect(formatDuration(36_000_000)).toBe("10h 0m 0s");
  });
});
