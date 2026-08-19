import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  fetchQueue,
  fetchQueueSummary,
  fetchQueueSubfolders,
  prioritizeSubfolder,
  clearCompleted,
  clearFailed,
} from "../../api/queue";

export default function QueuePage({ folderId }: { folderId: number | null }) {
  const queryClient = useQueryClient();
  const [selectedFolder, setSelectedFolder] = useState<number | null>(folderId);

  useEffect(() => {
    if (folderId !== null) setSelectedFolder(folderId);
  }, [folderId]);

  const { data: summaries } = useQuery({
    queryKey: ["queue-summary"],
    queryFn: () => fetchQueueSummary(),
    refetchInterval: 3000,
  });

  const { data: subfolders } = useQuery({
    queryKey: ["queue-subfolders", selectedFolder],
    queryFn: () => fetchQueueSubfolders(selectedFolder!),
    enabled: !!selectedFolder,
    refetchInterval: 5000,
  });

  const { data: queueItems } = useQuery({
    queryKey: ["queue-items", selectedFolder],
    queryFn: () => fetchQueue(selectedFolder ?? undefined, "pending", 50),
    enabled: !!selectedFolder,
    refetchInterval: 3000,
  });

  const bumpMutation = useMutation({
    mutationFn: ({ prefix, priority }: { prefix: string; priority: number }) =>
      prioritizeSubfolder(selectedFolder!, prefix, priority),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue-items"] });
      queryClient.invalidateQueries({ queryKey: ["queue-subfolders"] });
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => clearCompleted(selectedFolder ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue-summary"] }),
  });

  const clearFailedMutation = useMutation({
    mutationFn: () => clearFailed(selectedFolder ?? undefined),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue-summary"] }),
  });

  return (
    <div className="queue-page">
      <h2>Scan Queue</h2>

      {/* Summary */}
      <div className="queue-summary">
        {summaries?.map((s) => (
          <div
            key={s.folder_id}
            className={`queue-folder-card ${selectedFolder === s.folder_id ? "selected" : ""}`}
            onClick={() => setSelectedFolder(s.folder_id)}
          >
            <strong>{s.folder_path?.split("/").pop() || `Folder ${s.folder_id}`}</strong>
            <div className="queue-stats">
              <span className="stat pending">{s.pending} pending</span>
              <span className="stat processing">{s.processing} processing</span>
              <span className="stat completed">{s.completed} done</span>
              {s.failed > 0 && <span className="stat failed">{s.failed} failed</span>}
            </div>
          </div>
        ))}
        {summaries && summaries.length === 0 && <p>No items in queue.</p>}
      </div>

      {/* Subfolder prioritization */}
      {selectedFolder && subfolders && subfolders.length > 0 && (
        <div className="queue-subfolders">
          <h3>Subfolders (pending)</h3>
          <table className="queue-table">
            <thead>
              <tr>
                <th>Subfolder</th>
                <th>Pending</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {subfolders.map((sf) => (
                <tr key={sf.subfolder}>
                  <td>{sf.subfolder}</td>
                  <td>{sf.pending_count}</td>
                  <td>
                    <button
                      className="btn-bump"
                      onClick={() => bumpMutation.mutate({ prefix: sf.subfolder, priority: 100 })}
                    >
                      Bump to top
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pending items */}
      {selectedFolder && queueItems && queueItems.length > 0 && (
        <div className="queue-items">
          <h3>Next in queue</h3>
          <table className="queue-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              {queueItems.map((item) => (
                <tr key={item.id}>
                  <td title={item.file_path}>{item.relative_path}</td>
                  <td>{item.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {summaries && summaries.some((s) => s.completed > 0) && (
        <button className="btn-clear" onClick={() => clearMutation.mutate()}>
          Clear completed items
        </button>
      )}
      {summaries && summaries.some((s) => s.failed > 0) && (
        <button className="btn-clear btn-clear-failed" onClick={() => clearFailedMutation.mutate()}>
          Clear failed items
        </button>
      )}
    </div>
  );
}
