import type { ToolCallUI } from "../../store";

/**
 * 工具调用内联卡片：复刻旧前端 SSE tool_call_start/end 追加的 markdown 块引用视觉
 * （`> 🛠 正在调用工具/技能: name` / `> ✅ 执行结果: summary`），直接 JSX 输出。
 */
export default function ToolCallCard({ tc }: { tc: ToolCallUI }) {
  let argsParsed = tc.arguments || "{}";
  try {
    argsParsed = JSON.stringify(JSON.parse(argsParsed), null, 2);
  } catch {
    /* 非法 JSON：保留原文 */
  }
  const summary = (tc.resultSummary ?? "").replace(/\n/g, " ");
  const running = tc.status === "running";
  const rejected = tc.status === "rejected";
  const color = rejected ? "text-red-400" : running ? "text-cyber-blue" : "text-cyber-green";
  const icon = rejected ? "❌" : running ? "🛠" : "✅";
  const action = running ? "正在调用工具/技能" : "执行结果";

  return (
    <div className="flex animate-slide-up mb-2">
      <div className="max-w-3xl w-full chat-bubble-ai px-6 py-4 rounded-r-lg rounded-bl-lg shadow-sm text-zinc-400 font-mono text-[11px] leading-relaxed break-words">
        <div className={color}>
          {icon} <span className="font-bold">{action}</span>:{" "}
          <code className="text-cyber-blue">{tc.name}</code>
        </div>
        <div className="mt-1 text-zinc-500">参数:</div>
        <pre className="mt-1 bg-zinc-900/60 border border-zinc-800 rounded px-2 py-1.5 overflow-x-auto whitespace-pre-wrap">
          {argsParsed}
        </pre>
        {!running && summary && (
          <div className={`mt-2 ${color}`}>
            {rejected ? "操作已取消" : "↳"} {summary}
          </div>
        )}
      </div>
    </div>
  );
}
