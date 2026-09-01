import { useState } from "react";
import { useSession } from "../store";
import { apiFetch } from "../api/client";
import type { StatsResponse } from "../api/types";
import { usePolling } from "./usePolling";

/** /api/stats 轮询（3s，切换会话自动重启） */
export function useStats(): StatsResponse | null {
  const { currentSession } = useSession();
  const [stats, setStats] = useState<StatsResponse | null>(null);

  usePolling(
    async () => {
      const res = await apiFetch(`/api/stats?session=${encodeURIComponent(currentSession)}`);
      if (!res.ok) return;
      setStats((await res.json()) as StatsResponse);
    },
    3000,
    [currentSession]
  );

  return stats;
}
