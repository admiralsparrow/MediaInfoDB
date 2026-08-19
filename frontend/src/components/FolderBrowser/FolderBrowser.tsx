import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { fetchBrowse } from "../../api/browse";
import { addFolder } from "../../api/folders";
import type { BrowseEntry } from "../../types/folder";

interface Props {
  libraryId: number;
  libraryName: string;
  onClose: () => void;
}

export default function FolderBrowser({ libraryId, libraryName, onClose }: Props) {
  const [currentPath, setCurrentPath] = useState<string | undefined>(undefined);
  const [pathHistory, setPathHistory] = useState<(string | undefined)[]>([]);
  const [search, setSearch] = useState("");
  const queryClient = useQueryClient();

  const { data: entries, isLoading } = useQuery({
    queryKey: ["browse", currentPath],
    queryFn: () => fetchBrowse(currentPath),
  });

  const mutation = useMutation({
    mutationFn: (path: string) => addFolder(path, [libraryId]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      queryClient.invalidateQueries({ queryKey: ["media"] });
      queryClient.invalidateQueries({ queryKey: ["mediaCount"] });
      onClose();
    },
  });

  const filteredEntries = entries?.filter((e) =>
    e.name.toLowerCase().includes(search.toLowerCase())
  );

  function navigateTo(entry: BrowseEntry) {
    setPathHistory([...pathHistory, currentPath]);
    setCurrentPath(entry.path);
    setSearch("");
  }

  function goBack() {
    const prev = pathHistory[pathHistory.length - 1];
    setPathHistory(pathHistory.slice(0, -1));
    setCurrentPath(prev);
    setSearch("");
  }

  function handleAdd() {
    if (currentPath) {
      mutation.mutate(currentPath);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Folder to "{libraryName}"</h2>
          <button className="btn btn-sm" onClick={onClose}>
            &times;
          </button>
        </div>

        <div className="modal-path">
          {pathHistory.length > 0 && (
            <button className="btn btn-sm" onClick={goBack}>
              &larr; Back
            </button>
          )}
          <span className="current-path">{currentPath || "/"}</span>
        </div>

        <div className="modal-search">
          <input
            type="text"
            placeholder="Filter folders..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="search-input"
            autoComplete="off"
          />
        </div>

        <div className="modal-body">
          {isLoading && <p>Loading...</p>}
          {!isLoading && filteredEntries?.length === 0 && <p className="empty">No subdirectories</p>}
          <ul className="folder-list">
            {filteredEntries?.map((entry) => (
              <li key={entry.path} className="folder-entry">
                <button
                  className="folder-name"
                  onClick={() => navigateTo(entry)}
                >
                  {entry.name}
                  {entry.has_children && " >"}
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="modal-footer">
          {mutation.isError && (
            <p className="error">{(mutation.error as Error).message}</p>
          )}
          <button
            className="btn btn-primary"
            onClick={handleAdd}
            disabled={!currentPath || mutation.isPending}
          >
            {mutation.isPending ? "Adding..." : "Add This Folder"}
          </button>
        </div>
      </div>
    </div>
  );
}
