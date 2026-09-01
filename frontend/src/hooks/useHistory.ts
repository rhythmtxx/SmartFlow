import { useEffect, useRef } from "react";
import { useChat, useSession, type UIMessage } from "../store";
import { apiFetch } from "../api/client";
import type { HistoryMessage, HistoryResponse } from "../api/types";

/** 旧 JS fetchHistory（static/index.html 829-887 行）的 React 版：OpenAI 消息 → UIMessage[]（id 由 store 生成） */
function toUIMessages(msgs: HistoryMessage[]): Omit<UIMessage, "id">[] {
  const out: Omit<UIMessage, "id">[] = [];
  for (const msg of msgs) {
    if (msg.role === "system") continue; // Skip system prompts
    if (msg.role === "user") {
      const content = Array.isArray(msg.content)
        ? (msg.content.find((c) => c.type === "text")?.text ?? "")
        : (msg.content ?? "");
      out.push({ role: "user", content });
    } else if (msg.role === "assistant") {
      if (msg.content) out.push({ role: "assistant", content: msg.content });
      if (msg.tool_calls && msg.tool_calls.length > 0) {
        out.push({
          role: "tool",
          content: "",
          toolCalls: msg.tool_calls
            .filter((tc) => tc.type === "function")
            .map((tc) => ({
              id: tc.id,
              name: tc.function.name,
              arguments: tc.function.arguments,
              status: "done" as const,
            })),
        });
      }
    } else if (msg.role === "tool") {
      let res = msg.content || "执行完毕";
      if (res.length > 500) res = res.slice(0, 500) + "... (truncated for display)";
      out.push({
        role: "tool",
        content: "",
        toolCalls: [
          {
            id: msg.tool_call_id ?? msg.name ?? `tool-${out.length}`,
            name: msg.name ?? "tool",
            arguments: "{}",
            resultSummary: res.replace(/\n/g, " "),
            status: "done" as const,
          },
        ],
      });
    }
  }
  return out;
}

/** 挂载/切会话时拉 /api/history 恢复消息与 token（带会话竞态防护：过期响应丢弃） */
export function useHistory() {
  const { currentSession } = useSession();
  const { setMessages, setTokens } = useChat();
  const sessionRef = useRef(currentSession);
  sessionRef.current = currentSession;

  useEffect(() => {
    const session = currentSession;
    let cancelled = false;
    (async () => {
      const res = await apiFetch(`/api/history?session=${encodeURIComponent(session)}`);
      if (!res.ok || cancelled || sessionRef.current !== session) return;
      const data = (await res.json()) as HistoryResponse;
      if (cancelled || sessionRef.current !== session) return;
      if (data.tokens) setTokens(data.tokens);
      setMessages(toUIMessages(data.messages ?? []));
    })();
    return () => {
      cancelled = true;
    };
  }, [currentSession, setMessages, setTokens]);
}
