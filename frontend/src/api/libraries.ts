import { apiFetch } from "./client";
import type { Library } from "../types/folder";

export function fetchLibraries(): Promise<Library[]> {
  return apiFetch("/libraries");
}

export function createLibrary(name: string): Promise<Library> {
  return apiFetch("/libraries", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteLibrary(id: number): Promise<void> {
  return apiFetch(`/libraries/${id}`, { method: "DELETE" });
}

export function updateLibrary(id: number, name: string): Promise<Library> {
  return apiFetch(`/libraries/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}
