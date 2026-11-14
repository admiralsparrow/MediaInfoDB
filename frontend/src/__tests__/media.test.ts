/**
 * Tests for frontend api/media.ts utility functions and api/client.ts apiFetch.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We need to test applyMultipliers and injectTzOffset which are not exported.
// Instead, test through the exported functions by mocking apiFetch at the fetch level.

describe("apiFetch", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("calls fetch with correct URL and headers", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ data: "test" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const { apiFetch } = await import("../api/client");
    const result = await apiFetch("/test");

    expect(globalThis.fetch).toHaveBeenCalledWith("/api/v1/test", expect.objectContaining({
      headers: { "Content-Type": "application/json" },
    }));
    expect(result).toEqual({ data: "test" });
  });

  it("throws on non-ok response with detail", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not Found" }), {
        status: 404,
        statusText: "Not Found",
      })
    );

    const { apiFetch } = await import("../api/client");
    await expect(apiFetch("/missing")).rejects.toThrow("Not Found");
  });

  it("throws with statusText when JSON parse fails", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response("not json", {
        status: 500,
        statusText: "Internal Server Error",
      })
    );

    const { apiFetch } = await import("../api/client");
    await expect(apiFetch("/error")).rejects.toThrow("Internal Server Error");
  });

  it("returns undefined for 204 status", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response(null, {
        status: 204,
        headers: { "Content-Length": "0" },
      })
    );

    const { apiFetch } = await import("../api/client");
    const result = await apiFetch("/no-content");
    expect(result).toBeUndefined();
  });

  it("returns undefined for zero content-length", async () => {
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValue(
      new Response("", {
        status: 200,
        headers: { "Content-Length": "0" },
      })
    );

    const { apiFetch } = await import("../api/client");
    const result = await apiFetch("/empty");
    expect(result).toBeUndefined();
  });
});

describe("fetchMedia query construction", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("includes page, page_size, sort, order params", async () => {
    const { fetchMedia } = await import("../api/media");
    await fetchMedia({}, 2, 100, "title", "desc");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("page=2");
    expect(url).toContain("page_size=100");
    expect(url).toContain("sort=title");
    expect(url).toContain("order=desc");
  });

  it("applies multipliers to bitrate filters", async () => {
    const { fetchMedia } = await import("../api/media");
    // overall_bitrate has multiplier of 1_000_000 in filterDefinitions
    await fetchMedia({ overall_bitrate_min: "5" }, 1, 200, "file_name", "asc");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("overall_bitrate_min=5000000");
  });

  it("injects tz_offset for date filters", async () => {
    const { fetchMedia } = await import("../api/media");
    await fetchMedia({ scanned_at_min: "2024-01-01" }, 1, 200, "file_name", "asc");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("tz_offset=");
  });

  it("does not inject tz_offset without date filters", async () => {
    const { fetchMedia } = await import("../api/media");
    await fetchMedia({ "video.codec": "HEVC" }, 1, 200, "file_name", "asc");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).not.toContain("tz_offset");
  });

  it("passes non-multiplier filters unchanged", async () => {
    const { fetchMedia } = await import("../api/media");
    await fetchMedia({ "video.codec": "HEVC" }, 1, 200, "file_name", "asc");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("video.codec=HEVC");
  });
});

describe("fetchMediaCount", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ count: 42 }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns count from API", async () => {
    const { fetchMediaCount } = await import("../api/media");
    const result = await fetchMediaCount({});
    expect(result).toEqual({ count: 42 });
  });
});

describe("fetchMediaDetail", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1, file_name: "test.mkv" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetches detail for specific media ID", async () => {
    const { fetchMediaDetail } = await import("../api/media");
    const result = await fetchMediaDetail(1);

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("/media/1");
    expect(result).toEqual({ id: 1, file_name: "test.mkv" });
  });
});

describe("fetchFilterOptions", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ "video.codec": ["HEVC", "AVC"] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("fetches filter options without library", async () => {
    const { fetchFilterOptions } = await import("../api/media");
    await fetchFilterOptions();

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("/media/filters/options");
    expect(url).not.toContain("library_id");
  });

  it("includes library_id param", async () => {
    const { fetchFilterOptions } = await import("../api/media");
    await fetchFilterOptions(5);

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("library_id=5");
  });
});

describe("rescanFiles", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ message: "ok" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("sends POST with file_ids", async () => {
    const { rescanFiles } = await import("../api/media");
    await rescanFiles([1, 2, 3]);

    const [url, opts] = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(url).toContain("/media/rescan");
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({ file_ids: [1, 2, 3] });
  });
});

describe("fetchFolderChildren", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(["sub1", "sub2"]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("includes prefix param", async () => {
    const { fetchFolderChildren } = await import("../api/media");
    await fetchFolderChildren("shows/season1");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("prefix=");
  });

  it("includes library_id and search params", async () => {
    const { fetchFolderChildren } = await import("../api/media");
    await fetchFolderChildren("", 3, "test");

    const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(url).toContain("library_id=3");
    expect(url).toContain("search=test");
  });
});
