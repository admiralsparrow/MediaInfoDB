import { apiFetch } from "./client";

export interface ScanLogEntry {
  id: number;
  folder_id: number;
  folder_path: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  files_found: number;
  files_scanned: number;
  files_removed: number;
  error_message: string | null;
}

export interface ScanLogsResponse {
  total: number;
  items: ScanLogEntry[];
}

export interface ScanJobFile {
  id: number;
  file_name: string;
  relative_path: string;
}

export interface ScanJobFilesResponse {
  files: ScanJobFile[];
  removed_files: string[];
}

export function fetchScanLogs(params?: {
  folder_id?: number;
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.folder_id) searchParams.set("folder_id", String(params.folder_id));
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch<ScanLogsResponse>(`/logs${qs ? `?${qs}` : ""}`);
}

export function fetchScanJobFiles(jobId: number) {
  return apiFetch<ScanJobFilesResponse>(`/logs/${jobId}/files`);
}
