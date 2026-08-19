import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { rescanFolder } from "../../api/folders";
import { fetchLibraries } from "../../api/libraries";
import { apiFetch } from "../../api/client";
import type { Library } from "../../types/folder";
import LibrarySettings from "./LibrarySettings";

interface ActiveScan {
  id: number;
  folder_path: string;
  files_found: number;
  files_scanned: number;
}

interface Props {
  selectedLibraryId: number | null;
  onSelectLibrary: (id: number | null) => void;
  selectedFolderId: number | null;
  onSelectFolder: (id: number | null) => void;
}

export default function FolderList({ selectedLibraryId, onSelectLibrary, selectedFolderId, onSelectFolder }: Props) {
  const [showSettings, setShowSettings] = useState(false);
  const [triggeredFolders, setTriggeredFolders] = useState<Set<number>>(new Set());

  const { data: libraries } = useQuery({
    queryKey: ["libraries"],
    queryFn: fetchLibraries,
  });

  const { data: activeScans } = useQuery<ActiveScan[]>({
    queryKey: ["activeScans"],
    queryFn: () => apiFetch("/scans/active"),
    refetchInterval: 2000,
  });

  const activeFolderPaths = new Set(activeScans?.map((s) => s.folder_path) ?? []);

  const isFolderScanning = (folderPath: string, folderId: number) =>
    activeFolderPaths.has(folderPath) || triggeredFolders.has(folderId);

  const rescanMutation = useMutation({
    mutationFn: rescanFolder,
    onMutate: (folderId: number) => {
      setTriggeredFolders((prev) => new Set(prev).add(folderId));
    },
    onSettled: (_data, _error, folderId: number) => {
      setTimeout(() => {
        setTriggeredFolders((prev) => {
          const next = new Set(prev);
          next.delete(folderId);
          return next;
        });
      }, 5000);
    },
  });

  return (
    <div className="folder-list-panel">
      <div className="library-header">
        <h3>Libraries</h3>
        <div className="library-header-actions">
          <button className="btn btn-xs" onClick={() => setShowSettings(true)} title="Settings">&#9881;</button>
        </div>
      </div>

      <button
        className={`library-item ${selectedLibraryId === null ? "active" : ""}`}
        onClick={() => onSelectLibrary(null)}
      >
        All Libraries
      </button>

      {libraries?.map((lib) => (
        <LibraryEntry
          key={lib.id}
          library={lib}
          isSelected={selectedLibraryId === lib.id}
          onSelect={() => onSelectLibrary(lib.id)}
          onRescanFolder={(fId) => rescanMutation.mutate(fId)}
          isFolderScanning={isFolderScanning}
          selectedFolderId={selectedFolderId}
          onSelectFolder={onSelectFolder}
        />
      ))}

      {showSettings && (
        <LibrarySettings
          libraries={libraries || []}
          onClose={() => setShowSettings(false)}
          onLibraryDeleted={(id) => {
            if (selectedLibraryId === id) onSelectLibrary(null);
          }}
        />
      )}

    </div>
  );
}

interface LibraryEntryProps {
  library: Library;
  isSelected: boolean;
  onSelect: () => void;
  onRescanFolder: (id: number) => void;
  isFolderScanning: (folderPath: string, folderId: number) => boolean;
  selectedFolderId: number | null;
  onSelectFolder: (id: number | null) => void;
}

function LibraryEntry({ library, isSelected, onSelect, onRescanFolder, isFolderScanning, selectedFolderId, onSelectFolder }: LibraryEntryProps) {
  const hasFolderSelected = library.folders.some((f) => f.id === selectedFolderId);
  const [expanded, setExpanded] = useState(false);
  const showFolders = expanded || hasFolderSelected;
  const totalFiles = library.folders.reduce((sum, f) => sum + f.file_count, 0);

  return (
    <div className={`library-item-container ${isSelected ? "active" : ""}`}>
      <div className="library-item" onClick={onSelect}>
        <button className="library-expand" onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}>
          {showFolders ? "▾" : "▸"}
        </button>
        <div className="library-item-info">
          <span className="library-name">{library.name}</span>
          <span className="library-count">{library.folders.length} folders, {totalFiles} files</span>
        </div>
      </div>

      {showFolders && (
        <ul className="library-folders">
          {library.folders.map((f) => (
            <li key={f.id} className={`watched-folder ${selectedFolderId === f.id ? "active" : ""}`}>
              <div
                className="folder-info folder-clickable"
                onClick={() => onSelectFolder(selectedFolderId === f.id ? null : f.id)}
                title={`Filter to ${f.path}`}
              >
                <span className="folder-path" title={f.path}>
                  {f.path.split("/").pop() || f.path}
                </span>
                <span className="folder-count">{f.file_count} files</span>
              </div>
              <div className="folder-actions">
                <button
                  className="btn btn-xs"
                  onClick={() => onRescanFolder(f.id)}
                  disabled={isFolderScanning(f.path, f.id)}
                  title="Scan for new and changed files"
                >
                  {isFolderScanning(f.path, f.id) ? "Scanning..." : "Scan"}
                </button>
              </div>
            </li>
          ))}
          {library.folders.length === 0 && (
            <li className="empty" style={{ padding: "0.3rem 0", fontSize: "0.75rem" }}>No folders</li>
          )}
        </ul>
      )}
    </div>
  );
}
