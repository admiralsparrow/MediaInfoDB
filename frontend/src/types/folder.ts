export interface Folder {
  id: number;
  path: string;
  library_ids: number[];
  added_at: string;
  last_scanned: string | null;
  scan_interval_minutes: number | null;
  enabled: boolean;
  file_count: number;
}

export interface LibraryFolder {
  id: number;
  path: string;
  file_count: number;
  enabled: boolean;
}

export interface Library {
  id: number;
  name: string;
  created_at: string;
  folders: LibraryFolder[];
}

export interface BrowseEntry {
  name: string;
  path: string;
  has_children: boolean;
}
