import { useEffect, useRef } from "react";
import { useChat } from "../../store";
import { useHistory } from "../../hooks/useHistory";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";

const BOOT_CONTENT =
  "Greeting sequence activated. I am the SmartFlow agent core logic framework. Auxiliary tools registered. Skill matrices linked. Awaiting input directive.";

export default function ChatContainer() {
  const { messages, isGenerating } = useChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  useHistory(); // 挂载/切会话时恢复历史消息与 token

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  return (
    <>
      {/* Floating Tool Execution Indicator */}
      <div
        id="tool-float-card"
        className={`tool-indicator absolute top-6 inset-x-0 mx-auto w-max max-w-lg glass-panel text-zinc-200 border-cyber-blue/50 px-5 py-2.5 rounded shadow-[0_0_20px_rgba(0,240,255,0.15)] flex items-center space-x-4 pointer-events-none z-50 transition-opacity duration-300 ${
          isGenerating ? "opacity-100" : "opacity-0 -translate-y-4"
        }`}
      >
        <div className="relative w-4 h-4 rounded-full border border-cyber-blue/30 overflow-hidden">
          <div className="absolute inset-0 border-t border-cyber-blue rounded-full animate-radar-spin" />
        </div>
        <span id="tool-float-text" className="text-xs font-mono tracking-wide text-cyber-blue">
          Establishing localized link…
        </span>
      </div>

      {/* Chat Stream Workspace */}
      <div id="chat-container" ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-8 pb-32">
        {/* System Boot Message（旧 HTML 静态块） */}
        <div className="flex animate-slide-up">
          <div className="max-w-3xl chat-bubble-ai px-6 py-5 rounded-r-lg rounded-bl-lg shadow-sm text-zinc-300 font-mono text-sm leading-relaxed">
            <div className="text-[10px] text-cyber-blue/70 mb-2 uppercase tracking-widest flex items-center">
              <span className="w-1.5 h-1.5 bg-cyber-blue mr-2 rounded-full shadow-[0_0_5px_#00f0ff]" />
              System Override Initiated
            </div>
            <p>{BOOT_CONTENT}</p>
          </div>
        </div>
        {messages.map((m) => (
          <MessageBubble key={m.id} m={m} />
        ))}
      </div>

      <ChatInput />
    </>
  );
}
