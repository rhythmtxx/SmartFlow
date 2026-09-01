import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { usePolling } from "../../hooks/usePolling";
import { useSession } from "../../store";
import { apiFetch } from "../../api/client";
import type { MemoryResponse } from "../../api/types";

export default function MemoryPanel() {
  const { currentSession } = useSession();
  const [memory, setMemory] = useState<string>("");

  // I1 修复：会话切换时 usePolling 重启轮询，旧会话 in-flight 请求不会取消；
  // 用 ref 持有最新会话，响应到达后校验请求发起时的会话未变才落盘，变了就丢弃。
  const sessionRef = useRef(currentSession);
  useEffect(() => {
    sessionRef.current = currentSession;
  }, [currentSession]);

  usePolling(async () => {
    const session = sessionRef.current;
    const res = await apiFetch(`/api/memory?session=${encodeURIComponent(session)}`);
    if (!res.ok) return;
    const data = (await res.json()) as MemoryResponse;
    if (sessionRef.current !== session) return; // 会话已切换，丢弃过期响应
    setMemory(data.long_term_memory);
  }, 10000, [currentSession]);

  return (
    <div className="p-6 border-b border-cyber-border flex-1 overflow-y-auto">
      <h2 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-4 flex items-center">
        <svg className="w-3 h-3 mr-2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
          />
        </svg>
        Long-term Memory
      </h2>
      <div id="memory-content" className="prose prose-invert prose-sm font-sans text-xs text-zinc-400 leading-relaxed">
        {memory ? (
          <ReactMarkdown>{memory}</ReactMarkdown>
        ) : (
          <em className="text-zinc-600 font-mono">No persistent memory established...</em>
        )}
      </div>
    </div>
  );
}
