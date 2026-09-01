import type { ReactNode } from "react";
import { AuthProvider } from "./AuthContext";
import { SessionProvider } from "./SessionContext";
import { ChatProvider } from "./ChatContext";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <SessionProvider>
        <ChatProvider>{children}</ChatProvider>
      </SessionProvider>
    </AuthProvider>
  );
}

export { useAuth } from "./AuthContext";
export { useSession } from "./SessionContext";
export { useChat } from "./ChatContext";
export type { UIMessage, ToolCallUI, ApprovalRequired } from "./ChatContext";
