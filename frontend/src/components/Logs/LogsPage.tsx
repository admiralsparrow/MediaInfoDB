import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchScanLogs, fetchScanJobFiles, ScanLogEntry } from "../../api/logs";

export default function LogsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(0);
  const [expandedJob, setExpandedJob] = useState<number | null>(null);
  const pageSize = 50;

  const { data, isLoading } = useQuery({
    queryKey: ["scan-logs", statusFilter, page],
    queryFn: () =>
      fetchScanLogs({
        status: statusFilter || undefined,
        limit: pageSize,
        offset: page * pageSize,
      }),
    refetchInterval: 5000,
  });

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  const toggleExpand = (jobId: number) => {
    setExpandedJob(expandedJob === jobId ? null : jobId);
  };

  return (
    <div className="logs-page">
      <h2>Scan Logs</h2>

      <div className="logs-toolbar">
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(0);
          }}
        >
          <option value="">All statuses</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {isLoading && <p>Loading...</p>}

      {data && data.items.length === 0 && <p>No scan logs found.</p>}

      {data && data.items.length > 0 && (
        <>
          <table className="logs-table">
            <thead>
              <tr>
                <th></th>
                <th>Folder</th>
                <th>Status</th>
                <th>Started</th>
                <th>Duration</th>
                <th>Files Found</th>
                <th>Files Scanned</th>
                <th>Files Removed</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((entry) => (
                <LogRow
                  key={entry.id}
                  entry={entry}
                  isExpanded={expandedJob === entry.id}
                  onToggle={() => toggleExpand(entry.id)}
                />
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="logs-pagination">
              <button disabled={page === 0} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span>
                Page {page + 1} of {totalPages}
              </span>
              <button disabled={page >= totalPages - 1} onClick={() => setPage(page + 1)}>
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function LogRow({
  entry,
  isExpanded,
  onToggle,
}: {
  entry: ScanLogEntry;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const duration = formatDuration(entry.started_at, entry.finished_at);
  const folderName = entry.folder_path.split("/").pop() || entry.folder_path;

  return (
    <>
      <tr className={`log-row status-${entry.status}`} onClick={onToggle}>
        <td className="expand-cell">
          <span className={`expand-arrow ${isExpanded ? "expanded" : ""}`}>&#9654;</span>
        </td>
        <td title={entry.folder_path}>{folderName}</td>
        <td>
          <span className={`status-badge ${entry.status}`}>{entry.status}</span>
        </td>
        <td>{formatTime(entry.started_at)}</td>
        <td>{duration}</td>
        <td>{entry.files_found}</td>
        <td>{entry.files_scanned}</td>
        <td>{entry.files_removed || "—"}</td>
        <td className="error-cell" title={entry.error_message || ""}>
          {entry.error_message ? entry.error_message.slice(0, 60) : "—"}
        </td>
      </tr>
      {isExpanded && (
        <tr className="log-row-expanded">
          <td colSpan={9}>
            <ExpandedFiles jobId={entry.id} />
          </td>
        </tr>
      )}
    </>
  );
}

function ExpandedFiles({ jobId }: { jobId: number }) {
  const { data, isLoading } = useQuery({
    queryKey: ["scan-job-files", jobId],
    queryFn: () => fetchScanJobFiles(jobId),
  });

  if (isLoading) return <div className="expanded-files">Loading files...</div>;
  if (!data || (data.files.length === 0 && data.removed_files.length === 0 && data.rescanned_files.length === 0))
    return <div className="expanded-files">No files recorded for this scan job.</div>;

  const rescannedSet = new Set(data.rescanned_files);
  const importedFiles = data.files.filter((f) => !rescannedSet.has(f.file_name));

  return (
    <div className="expanded-files">
      {data.rescanned_files.length > 0 && (
        <>
          <div className="expanded-files-header">{data.rescanned_files.length} file(s) re-scanned</div>
          <ul className="expanded-files-list">
            {data.rescanned_files.map((name, i) => (
              <li key={`rescanned-${i}`} className="rescanned-file">{name}</li>
            ))}
          </ul>
        </>
      )}
      {importedFiles.length > 0 && (
        <>
          <div className="expanded-files-header">{importedFiles.length} file(s) imported</div>
          <ul className="expanded-files-list">
            {importedFiles.map((f) => (
              <li key={f.id}>{f.relative_path}</li>
            ))}
          </ul>
        </>
      )}
      {data.removed_files.length > 0 && (
        <>
          <div className="expanded-files-header">{data.removed_files.length} file(s) removed</div>
          <ul className="expanded-files-list">
            {data.removed_files.map((name, i) => (
              <li key={`removed-${i}`} className="removed-file">{name}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(start: string | null, end: string | null): string {
  if (!start) return "—";
  if (!end) return "in progress";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 1000) return "<1s";
  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSec = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainSec}s`;
  const hours = Math.floor(minutes / 60);
  const remainMin = minutes % 60;
  return `${hours}h ${remainMin}m`;
}
