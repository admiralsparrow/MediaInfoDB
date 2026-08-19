import { apiFetch } from "./client";
import type { Folder } from "../types/folder";

export function fetchFolders(): Promise<Folder[]> {
  return apiFetch("/folders");
}

export function addFolder(path: string, libraryIds: number[]): Promise<Folder> {
  return apiFetch("/folders", {
    method: "POST",
    body: JSON.stringify({ path, library_ids: libraryIds }),
  });
}

export function deleteFolder(id: number): Promise<void> {
  return apiFetch(`/folders/${id}`, { method: "DELETE" });
}

export function removeFolderFromLibrary(folderId: number, libraryId: number): Promise<void> {
  return apiFetch(`/folders/${folderId}/library/${libraryId}`, { method: "DELETE" });
}

export function rescanFolder(id: number): Promise<void> {
  return apiFetch(`/folders/${id}/rescan`, { method: "POST" });
}
