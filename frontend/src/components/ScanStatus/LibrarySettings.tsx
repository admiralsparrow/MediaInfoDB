import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { removeFolderFromLibrary } from "../../api/folders";
import { createLibrary, deleteLibrary, updateLibrary } from "../../api/libraries";
import type { Library } from "../../types/folder";
import FolderBrowser from "../FolderBrowser/FolderBrowser";

interface Props {
  libraries: Library[];
  onClose: () => void;
  onLibraryDeleted: (id: number) => void;
}

export default function LibrarySettings({ libraries, onClose, onLibraryDeleted }: Props) {
  const queryClient = useQueryClient();
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [newLibName, setNewLibName] = useState("");
  const [browseForLibrary, setBrowseForLibrary] = useState<{ id: number; name: string } | null>(null);
  const [confirmRemoveFolder, setConfirmRemoveFolder] = useState<{ folderId: number; libraryId: number } | null>(null);

  const createMutation = useMutation({
    mutationFn: (name: string) => createLibrary(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      setNewLibName("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteLibrary,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      onLibraryDeleted(id);
      setConfirmDeleteId(null);
    },
  });

  const renameMutation = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) => updateLibrary(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      setEditingId(null);
    },
  });

  const removeFolderMutation = useMutation({
    mutationFn: ({ folderId, libraryId }: { folderId: number; libraryId: number }) =>
      removeFolderFromLibrary(folderId, libraryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
      queryClient.invalidateQueries({ queryKey: ["media"] });
      queryClient.invalidateQueries({ queryKey: ["mediaCount"] });
      setConfirmRemoveFolder(null);
    },
  });

  function startRename(lib: Library) {
    setEditingId(lib.id);
    setEditName(lib.name);
  }

  function submitRename(id: number) {
    if (editName.trim() && editName.trim() !== libraries.find((l) => l.id === id)?.name) {
      renameMutation.mutate({ id, name: editName.trim() });
    } else {
      setEditingId(null);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal settings-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Library Settings</h2>
          <button className="btn btn-sm" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body settings-body">
          {libraries.length === 0 && (
            <div className="settings-empty">
              <p>No libraries yet</p>
              <p className="settings-empty-hint">Create one below to get started.</p>
            </div>
          )}

          {libraries.map((lib) => (
            <div key={lib.id} className="settings-card">
              <div className="settings-card-header">
                <div className="settings-card-title">
                  {editingId === lib.id ? (
                    <form
                      className="settings-rename-form"
                      onSubmit={(e) => { e.preventDefault(); submitRename(lib.id); }}
                    >
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="settings-rename-input"
                        autoComplete="off"
                        autoFocus
                        onBlur={() => submitRename(lib.id)}
                        onKeyDown={(e) => { if (e.key === "Escape") setEditingId(null); }}
                      />
                    </form>
                  ) : (
                    <span
                      className="settings-card-name"
                      onDoubleClick={() => startRename(lib)}
                      title="Double-click to rename"
                    >
                      {lib.name}
                    </span>
                  )}
                  <span className="settings-card-meta">
                    {lib.folders.length} {lib.folders.length === 1 ? "folder" : "folders"} &middot;{" "}
                    {lib.folders.reduce((sum, f) => sum + f.file_count, 0)} files
                  </span>
                </div>
                <div className="settings-card-actions">
                  <button className="btn btn-sm btn-ghost" onClick={() => startRename(lib)} title="Rename">
                    Rename
                  </button>
                  <button
                    className="btn btn-sm btn-ghost"
                    onClick={() => setBrowseForLibrary({ id: lib.id, name: lib.name })}
                    title="Add folder"
                  >
                    Add Folder
                  </button>
                  {confirmDeleteId === lib.id ? (
                    <div className="settings-confirm">
                      <span className="settings-confirm-text">Delete library?</span>
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => deleteMutation.mutate(lib.id)}
                        disabled={deleteMutation.isPending}
                      >
                        Yes, Delete
                      </button>
                      <button className="btn btn-sm btn-ghost" onClick={() => setConfirmDeleteId(null)}>
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button className="btn btn-sm btn-danger-ghost" onClick={() => setConfirmDeleteId(lib.id)}>
                      Delete
                    </button>
                  )}
                </div>
              </div>

              {lib.folders.length > 0 && (
                <div className="settings-card-folders">
                  {lib.folders.map((f) => (
                    <div key={f.id} className="settings-folder-row">
                      <div className="settings-folder-info">
                        <span className="settings-folder-path" title={f.path}>
                          {f.path}
                        </span>
                        <span className="settings-folder-count">{f.file_count} files</span>
                      </div>
                      {confirmRemoveFolder?.folderId === f.id && confirmRemoveFolder?.libraryId === lib.id ? (
                        <div className="settings-confirm">
                          <span className="settings-confirm-text">Remove?</span>
                          <button
                            className="btn btn-sm btn-danger"
                            onClick={() => removeFolderMutation.mutate({ folderId: f.id, libraryId: lib.id })}
                            disabled={removeFolderMutation.isPending}
                          >
                            Confirm
                          </button>
                          <button className="btn btn-sm btn-ghost" onClick={() => setConfirmRemoveFolder(null)}>
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          className="btn btn-sm btn-danger-ghost"
                          onClick={() => setConfirmRemoveFolder({ folderId: f.id, libraryId: lib.id })}
                          title="Remove folder from library"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {lib.folders.length === 0 && (
                <div className="settings-card-empty">
                  No folders added yet.{" "}
                  <button
                    className="btn-link"
                    onClick={() => setBrowseForLibrary({ id: lib.id, name: lib.name })}
                  >
                    Add one
                  </button>
                </div>
              )}
            </div>
          ))}

          <form
            className="settings-create-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (newLibName.trim()) createMutation.mutate(newLibName.trim());
            }}
          >
            <input
              type="text"
              value={newLibName}
              onChange={(e) => setNewLibName(e.target.value)}
              placeholder="New library name..."
              className="settings-create-input"
              autoComplete="off"
            />
            <button
              className="btn btn-sm btn-primary"
              type="submit"
              disabled={!newLibName.trim() || createMutation.isPending}
            >
              Create Library
            </button>
          </form>
        </div>
      </div>

      {browseForLibrary && (
        <FolderBrowser
          libraryId={browseForLibrary.id}
          libraryName={browseForLibrary.name}
          onClose={() => setBrowseForLibrary(null)}
        />
      )}
    </div>
  );
}
