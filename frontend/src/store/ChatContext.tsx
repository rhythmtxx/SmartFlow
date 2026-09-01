import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import type { ChatEvent } from "../api/types";

export type ApprovalRequired = Extract<ChatEvent, { type: "approval_required" }>;

export interface ToolCallUI {
  id: string;
  name: string;
  arguments: string;
  resultSummary?: string;
  status: "running" | "done" | "rejected";
}
export interface UIMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  toolCalls?: ToolCallUI[];
}

interface ChatState {
  messages: UIMessage[];
  cumulativeTokens: { prompt: number; completion: number };
  isGenerating: boolean;
  pendingApproval: ApprovalRequired | null;
  appendMessage: (m: Omit<UIMessage, "id">) => void;
  setMessages: (msgs: Omit<UIMessage, "id">[]) => void;
  updateToolCall: (id: string, patch: Partial<ToolCallUI>) => void;
  addTokens: (t: { prompt: number; completion: number }) => void;
  setTokens: (t: { prompt: number; completion: number }) => void;
  resetTokens: () => void;
  setIsGenerating: (v: boolean) => void;
  setPendingApproval: (a: ApprovalRequired | null) => void;
  clearMessages: () => void;
}
const Ctx = createContext<ChatState | null>(null);
let seq = 0;
const uid = () => `m${++seq}-${Date.now()}`;

export function ChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessagesState] = useState<UIMessage[]>([]);
  const [cumulativeTokens, setTokensState] = useState({ prompt: 0, completion: 0 });
  const [isGenerating, setGenerating] = useState(false);
  const [pendingApproval, setPending] = useState<ApprovalRequired | null>(null);

  const appendMessage: ChatState["appendMessage"] = useCallback((m) => {
    setMessagesState((prev) => [...prev, { ...m, id: uid() }]);
  }, []);

  const setMessages: ChatState["setMessages"] = useCallback(
    (msgs) => setMessagesState(msgs.map((m) => ({ ...m, id: uid() }))),
    []
  );

  const updateToolCall: ChatState["updateToolCall"] = useCallback((id, patch) => {
    setMessagesState((prev) =>
      prev.map((m) =>
        m.toolCalls
          ? { ...m, toolCalls: m.toolCalls.map((tc) => (tc.id === id ? { ...tc, ...patch } : tc)) }
          : m
      )
    );
  }, []);

  const addTokens: ChatState["addTokens"] = useCallback((t) => {
    setTokensState((prev) => ({
      prompt: prev.prompt + t.prompt,
      completion: prev.completion + t.completion,
    }));
  }, []);

  const setTokens: ChatState["setTokens"] = useCallback((t) => setTokensState(t), []);
  const resetTokens: ChatState["resetTokens"] = useCallback(
    () => setTokensState({ prompt: 0, completion: 0 }),
    []
  );
  const clearMessages: ChatState["clearMessages"] = useCallback(() => setMessagesState([]), []);

  return (
    <Ctx.Provider
      value={{
        messages,
        cumulativeTokens,
        isGenerating,
        pendingApproval,
        appendMessage,
        setMessages,
        updateToolCall,
        addTokens,
        setTokens,
        resetTokens,
        setIsGenerating: setGenerating,
        setPendingApproval: setPending,
        clearMessages,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}

export function useChat() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useChat must be used within ChatProvider");
  return v;
}
