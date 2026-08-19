import { apiFetch } from "./client";

export interface QueueItem {
  id: number;
  folder_id: number;
  file_path: string;
  relative_path: string;
  priority: number;
  status: string;
  error_message: string | null;
}

export interface QueueSummary {
  folder_id: number;
  folder_path: string;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface SubfolderInfo {
  subfolder: string;
  pending_count: number;
}

export function fetchQueue(folderId?: number, status = "pending", limit = 100, offset = 0) {
  const params = new URLSearchParams({ status, limit: String(limit), offset: String(offset) });
  if (folderId) params.set("folder_id", String(folderId));
  return apiFetch<QueueItem[]>(`/queue?${params}`);
}

export function fetchQueueSummary(folderId?: number) {
  const params = folderId ? `?folder_id=${folderId}` : "";
  return apiFetch<QueueSummary[]>(`/queue/summary${params}`);
}

export function fetchQueueSubfolders(folderId: number) {
  return apiFetch<SubfolderInfo[]>(`/queue/subfolders?folder_id=${folderId}`);
}

export function setItemPriority(itemId: number, priority: number) {
  return apiFetch(`/queue/${itemId}/priority`, {
    method: "PATCH",
    body: JSON.stringify({ priority }),
  });
}

export function prioritizeSubfolder(folderId: number, prefix: string, priority: number) {
  return apiFetch(`/queue/prioritize-subfolder`, {
    method: "POST",
    body: JSON.stringify({ folder_id: folderId, prefix, priority }),
  });
}

export function clearCompleted(folderId?: number) {
  const params = folderId ? `?folder_id=${folderId}` : "";
  return apiFetch(`/queue/completed${params}`, { method: "DELETE" });
}

export function clearFailed(folderId?: number) {
  const params = folderId ? `?folder_id=${folderId}` : "";
  return apiFetch(`/queue/failed${params}`, { method: "DELETE" });
}
