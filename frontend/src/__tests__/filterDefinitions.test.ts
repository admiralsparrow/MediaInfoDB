import { describe, it, expect } from "vitest";
import { filterDefinitions } from "../components/Filters/filterDefinitions";


describe("filterDefinitions", () => {
  it("has unique keys", () => {
    const keys = filterDefinitions.map((f) => f.key);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("has unique apiParams", () => {
    const params = filterDefinitions.map((f) => f.apiParam);
    expect(new Set(params).size).toBe(params.length);
  });

  it("all types are valid", () => {
    const validTypes = ["enum", "boolean", "text", "number_min", "number_max", "range", "date_range"];
    for (const def of filterDefinitions) {
      expect(validTypes).toContain(def.type);
    }
  });

  it("all groups are valid", () => {
    const validGroups = ["general", "video", "audio", "subtitle"];
    for (const def of filterDefinitions) {
      expect(validGroups).toContain(def.group);
    }
  });

  it("range filters have apiParamMax", () => {
    const rangeFilters = filterDefinitions.filter((f) => f.type === "range" || f.type === "date_range");
    for (const def of rangeFilters) {
      expect(def.apiParamMax).toBeTruthy();
    }
  });

  it("range filters with multiplier have numeric multiplier", () => {
    const withMultiplier = filterDefinitions.filter((f) => f.multiplier !== undefined);
    for (const def of withMultiplier) {
      expect(typeof def.multiplier).toBe("number");
      expect(def.multiplier).toBeGreaterThan(0);
    }
  });

  it("covers all expected groups", () => {
    const groups = new Set(filterDefinitions.map((f) => f.group));
    expect(groups).toContain("general");
    expect(groups).toContain("video");
    expect(groups).toContain("audio");
    expect(groups).toContain("subtitle");
  });

  it("includes core filters", () => {
    const keys = filterDefinitions.map((f) => f.key);
    expect(keys).toContain("video.codec");
    expect(keys).toContain("audio.codec");
    expect(keys).toContain("subtitle.language");
    expect(keys).toContain("source");
    expect(keys).toContain("provider");
    expect(keys).toContain("video.hdr10");
    expect(keys).toContain("video.dolby_vision");
    expect(keys).toContain("audio.is_atmos");
  });

  it("boolean filters have no multiplier", () => {
    const boolFilters = filterDefinitions.filter((f) => f.type === "boolean");
    for (const def of boolFilters) {
      expect(def.multiplier).toBeUndefined();
    }
  });
});
