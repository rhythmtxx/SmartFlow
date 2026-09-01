import ReactMarkdown from "react-markdown";
import type { UIMessage } from "../../store";
import ToolCallCard from "./ToolCallCard";

export default function MessageBubble({ m }: { m: UIMessage }) {
  if (m.role === "tool") {
    return (
      <>
        {(m.toolCalls ?? []).map((tc) => (
          <ToolCallCard key={tc.id} tc={tc} />
        ))}
      </>
    );
  }

  if (m.role === "user") {
    return (
      <div className="flex justify-end animate-slide-up mb-4">
        <div className="max-w-2xl chat-bubble-user px-5 py-3 rounded-l-lg rounded-tr-lg shadow-md text-zinc-200">
          <p className="whitespace-pre-wrap font-sans text-[15px]">{m.content}</p>
        </div>
      </div>
    );
  }

  if (m.role === "system") {
    return (
      <div className="flex animate-slide-up mb-4">
        <div className="max-w-3xl chat-bubble-ai px-6 py-4 border border-cyber-border rounded-r-lg rounded-bl-lg shadow-sm text-zinc-500 font-mono text-[11px] leading-relaxed italic">
          <p>{m.content}</p>
        </div>
      </div>
    );
  }

  // assistant：流式气泡 + markdown（旧 createAssistantBubble / appendAssistantText）
  return (
    <div className="flex animate-slide-up mb-2">
      <div className="max-w-3xl chat-bubble-ai px-6 py-5 rounded-r-lg rounded-bl-lg shadow-sm text-zinc-300 font-sans text-[15px] leading-relaxed prose prose-invert prose-sm break-words">
        <ReactMarkdown>{m.content}</ReactMarkdown>
      </div>
    </div>
  );
}
