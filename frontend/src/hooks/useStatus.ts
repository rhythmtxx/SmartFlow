import { useState } from "react";
import { usePolling } from "./usePolling";
import { apiFetch } from "../api/client";
import type { StatusResponse } from "../api/types";

/**
 * /api/status 轮询：skills + tools（旧 JS fetchStatus 的 React 版）。
 */
export function useStatus() {
  const [skills, setSkills] = useState<StatusResponse["skills"]>([]);
  const [tools, setTools] = useState<StatusResponse["tools"]>([]);

  usePolling(async () => {
    const res = await apiFetch("/api/status");
    if (!res.ok) return;
    const data = (await res.json()) as StatusResponse;
    setSkills(data.skills);
    setTools(data.tools);
  }, 10000, []);

  return { skills, tools };
}
