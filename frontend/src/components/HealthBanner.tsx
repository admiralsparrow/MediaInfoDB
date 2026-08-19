import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";

function fetchHealth(): Promise<{ status: string }> {
  return apiFetch("/health");
}

export default function HealthBanner() {
  const { isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 10000,
    retry: 2,
  });

  if (!isError) return null;

  return (
    <div className="health-banner">
      <span className="health-banner-icon">&#9888;</span>
      <span>Database unreachable — some features may be unavailable</span>
    </div>
  );
}
