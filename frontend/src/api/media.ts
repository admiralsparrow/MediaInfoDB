import { apiFetch } from "./client";
import type { MediaFileDetail } from "../types/media";
import { filterDefinitions } from "../components/Filters/filterDefinitions";

const MULTIPLIER_MAP: Record<string, number> = {};
for (const def of filterDefinitions) {
  if (def.multiplier) {
    MULTIPLIER_MAP[def.apiParam] = def.multiplier;
    if (def.apiParamMax) {
      MULTIPLIER_MAP[def.apiParamMax] = def.multiplier;
    }
  }
}

function applyMultipliers(filters: Record<string, string>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(filters)) {
    if (value && MULTIPLIER_MAP[key]) {
      const num = parseFloat(value);
      result[key] = isNaN(num) ? value : String(Math.round(num * MULTIPLIER_MAP[key]));
    } else {
      result[key] = value;
    }
  }
  return result;
}

function injectTzOffset(filters: Record<string, string>): Record<string, string> {
  const hasDate = Object.keys(filters).some(
    (k) => k.startsWith("scanned_at") || k.startsWith("file_modified_at")
  );
  if (!hasDate) return filters;
  return { ...filters, tz_offset: String(new Date().getTimezoneOffset()) };
}

export function fetchMedia(
  filters: Record<string, string>,
  page = 1,
  pageSize = 200,
  sort = "file_name",
  order = "asc"
): Promise<MediaFileDetail[]> {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    sort,
    order,
    ...injectTzOffset(applyMultipliers(filters)),
  });
  return apiFetch(`/media?${params}`);
}

export function fetchMediaCount(
  filters: Record<string, string>
): Promise<{ count: number }> {
  const params = new URLSearchParams(injectTzOffset(applyMultipliers(filters)));
  return apiFetch(`/media/count?${params}`);
}

export function fetchMediaDetail(id: number): Promise<MediaFileDetail> {
  return apiFetch(`/media/${id}`);
}

export function fetchFilterOptions(libraryId?: number | null): Promise<Record<string, string[]>> {
  const params = libraryId ? `?library_id=${libraryId}` : "";
  return apiFetch(`/media/filters/options${params}`);
}

export function fetchFolderChildren(prefix: string, libraryId?: number | null, search?: string): Promise<string[]> {
  const params = new URLSearchParams();
  if (prefix) params.set("prefix", prefix);
  if (libraryId) params.set("library_id", String(libraryId));
  if (search) params.set("search", search);
  return apiFetch(`/media/folders/children?${params}`);
}

export function rescanFiles(fileIds: number[]): Promise<{ message: string }> {
  return apiFetch("/media/rescan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds }),
  });
}
