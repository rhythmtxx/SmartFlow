import { useCallback, useRef, useState } from "react";
import { apiFetch } from "../api/client";
import { useChat, useSession } from "../store";
import type { ChatEvent } from "../api/types";

/** 纯函数：把 chunk 追加到 buffer，切出完整 SSE 事件，保留未闭合尾部。 */
export function feedStream(
  buffer: string,
  chunk: string
): { events: ChatEvent[]; buffer: string } {
  const buf = buffer + chunk;
  const parts = buf.split("\n\n");
  const rest = parts.pop() ?? "";
  const events: ChatEvent[] = [];
  for (const part of parts) {
    const line = part.trim();
    if (!line.startsWith("data:")) continue;
    const json = line.slice(5).trim();
    if (!json) continue;
    try {
      events.push(JSON.parse(json) as ChatEvent);
    } catch {
      /* 非法 JSON：丢弃该事件，不崩溃 */
    }
  }
  return { events, buffer: rest };
}

/**
 * SSE 流式聊天：POST /api/chat（fetch + ReadableStream，非 EventSource——
 * 需带 Authorization 头 + POST body），增量解析 data: 事件并派发到 ChatContext。
 */
export function useChatStream() {
  const { currentSession } = useSession();
  const chat = useChat();
  const [isGenerating, setIsGenerating] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const handleEvent = useCallback(
    (e: ChatEvent) => {
      switch (e.type) {
        case "text_delta":
          chat.appendMessage({ role: "assistant", content: e.content });
          break;
        case "tool_call_start":
          chat.appendMessage({
            role: "tool",
            content: "",
            toolCalls: [{ id: e.id, name: e.name, arguments: e.arguments, status: "running" }],
          });
          break;
        case "tool_call_end":
          chat.updateToolCall(e.id, {
            resultSummary: e.result_summary,
            status: e.approved === false ? "rejected" : "done",
          });
          break;
        case "approval_required":
          chat.setPendingApproval(e);
          break;
        case "approval_resolved":
          chat.updateToolCall(e.id, {
            resultSummary: e.approved ? undefined : "用户拒绝或超时，操作已取消",
            status: e.approved ? "done" : "rejected",
          });
          chat.setPendingApproval(null);
          break;
        case "token_usage":
          chat.addTokens({ prompt: e.prompt_tokens, completion: e.completion_tokens });
          break;
        case "error":
          chat.appendMessage({ role: "system", content: `⚠️ ${e.content}` });
          break;
        case "turn_end":
          break;
      }
    },
    [chat]
  );

  const send = useCallback(
    async (text: string) => {
      const controller = new AbortController();
      abortRef.current = controller;
      setIsGenerating(true);
      try {
        const res = await apiFetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, session: currentSession }),
          signal: controller.signal,
        });
        if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
        const reader = res.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          const { events, buffer: rest } = feedStream(buffer, decoder.decode(value, { stream: true }));
          buffer = rest;
          events.forEach(handleEvent);
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          chat.appendMessage({ role: "system", content: `⚠️ 请求失败: ${(err as Error).message}` });
        }
      } finally {
        setIsGenerating(false);
        abortRef.current = null;
      }
    },
    [chat, currentSession, handleEvent]
  );

  return { send, isGenerating };
}
