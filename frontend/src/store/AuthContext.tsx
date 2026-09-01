import { createContext, useContext, useState, type ReactNode } from "react";
import { getToken, setToken as persistToken } from "../api/client";

interface AuthState {
  apiToken: string;
  setApiToken: (t: string) => void;
}
const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [apiToken, setApiTokenState] = useState<string>(() => getToken());
  const setApiToken = (t: string) => {
    setApiTokenState(t);
    persistToken(t);
  };
  return <Ctx.Provider value={{ apiToken, setApiToken }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used within AuthProvider");
  return v;
}
