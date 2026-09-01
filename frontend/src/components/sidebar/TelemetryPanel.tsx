import { useChat } from "../../store";
import { apiFetch } from "../../api/client";
import { useSession } from "../../store";
import { useStats } from "../../hooks/useStats";

const pad0 = (num: number) => String(num).padStart(4, "0");

/** 风险着色：exec=high(红) write/edit=medium(黄) 其他=low(绿)——与旧 JS 一致 */
function riskColor(tool: string): string {
  if (tool === "exec") return "text-red-400";
  if (tool.startsWith("write") || tool.startsWith("edit")) return "text-yellow-400";
  return "text-cyber-green";
}

export default function TelemetryPanel() {
  const { cumulativeTokens, clearMessages, resetTokens, appendMessage } = useChat();
  const { currentSession } = useSession();
  const stats = useStats();

  const totals = stats?.totals;
  const recent = stats?.recent_tool_calls ?? [];
  const cost = totals?.estimated_cost != null ? `¥${totals.estimated_cost.toFixed(4)}` : "¥--";

  const purge = async () => {
    await apiFetch(`/api/clear?session=${encodeURIComponent(currentSession)}`, {
      method: "POST",
    });
    clearMessages();
    resetTokens();
    appendMessage({ role: "system", content: "SYS_OP: Memory wiped successfully." });
  };

  return (
    <div className="p-6 border-b border-cyber-border">
      <h2 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-4 flex items-center">
        <svg
          className="w-3 h-3 mr-2 text-zinc-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M13 10V3L4 14h7v7l9-11h-7z"
          />
        </svg>
        Telemetry Data
      </h2>
      <div className="space-y-4 font-mono text-sm">
        <div className="flex justify-between items-end border-b border-zinc-800/50 pb-2">
          <span className="text-zinc-400 text-xs">TX_PROMPT</span>
          <span id="token-prompt" className="text-cyber-green">
            {pad0(cumulativeTokens.prompt)}
          </span>
        </div>
        <div className="flex justify-between items-end border-b border-zinc-800/50 pb-2">
          <span className="text-zinc-400 text-xs">RX_COMPLETION</span>
          <span id="token-completion" className="text-cyber-blue">
            {pad0(cumulativeTokens.completion)}
          </span>
        </div>
        <div className="flex justify-between items-end pt-1">
          <span className="font-bold text-zinc-300 text-xs">TOTAL_BANDWIDTH</span>
          <span id="token-total" className="font-bold text-white tracking-wider">
            {pad0(cumulativeTokens.prompt + cumulativeTokens.completion)}
          </span>
        </div>
        <div className="flex justify-between items-end pt-1">
          <span className="font-bold text-zinc-300 text-xs">COST_ESTIMATE</span>
          <span id="cost-estimate" className="font-bold text-cyber-purple tracking-wider">
            {cost}
          </span>
        </div>
      </div>

      {/* Tool Calls 统计与时间线 */}
      <div className="mt-5">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 flex items-center">
            <svg
              className="w-3 h-3 mr-2 text-zinc-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            Tool Calls
            <span
              id="tool-calls-count"
              className="ml-2 text-cyber-blue normal-case tracking-normal"
            >
              {totals?.tool_calls ?? 0}
            </span>
          </h3>
        </div>
        <ul id="tool-calls-list" className="space-y-1.5 max-h-32 overflow-y-auto">
          {recent.length === 0 ? (
            <li className="text-[10px] text-zinc-600 font-mono italic">No tool calls recorded.</li>
          ) : (
            recent.map((t, i) => {
              const tool = t.tool || "unknown";
              const summary = t.result_summary || "";
              const ok = !summary.includes("错误") && !summary.includes("失败");
              return (
                <li
                  key={`${t.created_at}-${i}`}
                  className="flex items-center justify-between text-[10px] font-mono border-b border-zinc-900/50 pb-1 last:border-0"
                >
                  <span className={`${riskColor(tool)} truncate max-w-[55%]`}>{tool}()</span>
                  <span className="text-zinc-600 flex-shrink-0 truncate max-w-[45%]">
                    {ok ? "✓" : "✗"} {summary.slice(0, 24)}
                  </span>
                </li>
              );
            })
          )}
        </ul>
      </div>

      {/* Purge Memory（旧 DOM 中位于 API Token 之后；组合处 ApiTokenInput 渲染在本面板之前） */}
      <button
        type="button"
        onClick={() => void purge()}
        className="mt-6 w-full py-2.5 bg-zinc-900 border border-zinc-700 hover:border-cyber-blue hover:text-cyber-blue active:bg-zinc-800 focus-visible:ring-1 focus-visible:ring-cyber-blue focus:outline-none text-zinc-400 text-xs font-mono tracking-widest uppercase rounded-sm transition-all duration-300 relative overflow-hidden group"
      >
        <span className="relative z-10">Purge Memory</span>
        <div className="absolute inset-0 bg-cyber-blue/10 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
      </button>
    </div>
  );
}
