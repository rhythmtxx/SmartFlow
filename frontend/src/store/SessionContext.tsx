import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { apiFetch } from "../api/client";
import type { SessionItem } from "../api/types";

const SESSION_KEY = "smartflow_session_id";

interface SessionState {
  currentSession: string;
  sessions: SessionItem[];
  setCurrentSession: (id: string) => void;
  refreshSessions: () => Promise<void>;
  createSession: () => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
}
const Ctx = createContext<SessionState | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [currentSession, setCurrent] = useState<string>(
    () => localStorage.getItem(SESSION_KEY) ?? "default"
  );
  const [sessions, setSessions] = useState<SessionItem[]>([]);

  const setCurrentSession = useCallback((id: string) => {
    setCurrent(id);
    localStorage.setItem(SESSION_KEY, id);
  }, []);

  const refreshSessions = useCallback(async () => {
    const res = await apiFetch("/api/sessions");
    if (!res.ok) return;
    const data = (await res.json()) as { sessions: SessionItem[] };
    setSessions(data.sessions);
  }, []);

  const createSession = useCallback(async () => {
    await refreshSessions();
    const res = await apiFetch("/api/sessions", { method: "POST" });
    if (!res.ok) return;
    const data = (await res.json()) as { session_id: string };
    setCurrentSession(data.session_id);
    await refreshSessions();
  }, [refreshSessions, setCurrentSession]);

  const deleteSession = useCallback(
    async (id: string) => {
      await apiFetch(`/api/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (id === currentSession) setCurrentSession("default");
      await refreshSessions();
    },
    [currentSession, refreshSessions, setCurrentSession]
  );

  return (
    <Ctx.Provider
      value={{
        currentSession,
        sessions,
        setCurrentSession,
        refreshSessions,
        createSession,
        deleteSession,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useSession() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession must be used within SessionProvider");
  return v;
}
