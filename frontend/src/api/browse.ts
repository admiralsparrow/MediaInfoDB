import { apiFetch } from "./client";
import type { BrowseEntry } from "../types/folder";

export function fetchBrowse(path?: string): Promise<BrowseEntry[]> {
  const params = path ? `?path=${encodeURIComponent(path)}` : "";
  return apiFetch(`/browse${params}`);
}
