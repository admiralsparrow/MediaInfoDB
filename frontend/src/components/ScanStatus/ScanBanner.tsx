import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";
import { apiFetch } from "../../api/client";

interface ActiveScan {
  id: number;
  folder_id: number;
  folder_path: string;
  phase: "discovering" | "scanning";
  files_found: number;
  files_scanned: number;
}

function fetchActiveScans(): Promise<ActiveScan[]> {
  return apiFetch("/scans/active");
}

interface Props {
  onNavigateToQueue?: (folderId: number | null) => void;
}

export default function ScanBanner({ onNavigateToQueue }: Props) {
  const queryClient = useQueryClient();
  const wasScanning = useRef(false);

  const { data: scans } = useQuery({
    queryKey: ["activeScans"],
    queryFn: fetchActiveScans,
    refetchInterval: 2000,
  });

  const isScanning = (scans?.length ?? 0) > 0;

  useEffect(() => {
    if (wasScanning.current && !isScanning) {
      queryClient.invalidateQueries({ queryKey: ["media"] });
      queryClient.invalidateQueries({ queryKey: ["mediaCount"] });
      queryClient.invalidateQueries({ queryKey: ["libraries"] });
    }
    wasScanning.current = isScanning;
  }, [isScanning, queryClient]);

  if (!scans?.length) return null;

  const discovering = scans.filter((s) => s.phase === "discovering");
  const scanning = scans.filter((s) => s.phase === "scanning");
  const totalFound = scanning.reduce((s, j) => s + j.files_found, 0);
  const totalScanned = scanning.reduce((s, j) => s + j.files_scanned, 0);

  const folderName = (s: ActiveScan) => s.folder_path.split("/").pop();

  return (
    <div className="scan-banner" onClick={() => onNavigateToQueue?.(scans[0]?.folder_id ?? null)} style={{ cursor: "pointer" }}>
      <span className="scan-banner-spinner" />
      <span>
        {discovering.length > 0 && scanning.length === 0 && (
          <>
            Checking for new/modified files
            {discovering.length === 1 && (
              <span className="scan-banner-path"> in {folderName(discovering[0])}</span>
            )}
          </>
        )}
        {scanning.length > 0 && (
          <>
            Scanning {totalScanned}/{totalFound} files
            {scanning.length === 1 && (
              <span className="scan-banner-path"> from {folderName(scanning[0])}</span>
            )}
          </>
        )}
        {discovering.length > 0 && scanning.length > 0 && (
          <span className="scan-banner-path">
            {" "}(checking {discovering.length} more {discovering.length === 1 ? "folder" : "folders"})
          </span>
        )}
      </span>
    </div>
  );
}
