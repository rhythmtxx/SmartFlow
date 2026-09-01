import { useSession } from "../../store";
import { useChat } from "../../store";
import { usePolling } from "../../hooks/usePolling";

/** 切换会话：切换 + 清空消息区 + 重置 token（历史恢复由 ChatContainer 依赖 currentSession 自动触发） */
function useSwitchSession() {
  const { setCurrentSession } = useSession();
  const { clearMessages, resetTokens } = useChat();
  return (id: string) => {
    setCurrentSession(id);
    clearMessages();
    resetTokens();
  };
}

export default function SessionsPanel() {
  const { currentSession, sessions, refreshSessions, createSession, deleteSession } = useSession();
  const switchSession = useSwitchSession();

  usePolling(refreshSessions, 30000, []);

  return (
    <div className="p-6 border-b border-cyber-border">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 flex items-center">
          <svg className="w-3 h-3 mr-2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          Sessions
        </h2>
        <button
          type="button"
          onClick={() => void createSession()}
          title="新建会话"
          className="text-zinc-400 hover:text-cyber-green transition-colors focus:outline-none cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
          </svg>
        </button>
      </div>
      <ul id="sessions-list" className="space-y-1.5 max-h-40 overflow-y-auto">
        {sessions.length === 0 ? (
          <li className="text-xs text-zinc-600 font-mono italic">Loading sessions...</li>
        ) : (
          sessions.map((s) => {
            const active = s.session_id === currentSession;
            const label = s.session_id === "default" ? "default" : s.session_id.slice(0, 8);
            return (
              <li
                key={s.session_id}
                onClick={() => switchSession(s.session_id)}
                className={`group flex items-center justify-between px-2.5 py-1.5 rounded-sm cursor-pointer border transition-all duration-200 ${
                  active
                    ? "bg-zinc-800/80 border-cyber-blue/40 text-cyber-blue"
                    : "bg-zinc-900/40 border-transparent text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                }`}
              >
                <span className="flex items-center min-w-0">
                  <span
                    className={`w-1.5 h-1.5 rounded-full mr-2 flex-shrink-0 ${
                      active ? "bg-cyber-blue shadow-[0_0_4px_#00f0ff]" : "bg-zinc-600"
                    }`}
                  />
                  <span className="font-mono text-[11px] truncate">{label}</span>
                </span>
                <span className="flex items-center flex-shrink-0 ml-2">
                  <span className="text-[9px] font-mono text-zinc-600 mr-1.5">{s.message_count || 0}</span>
                  {s.session_id !== "default" && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        void deleteSession(s.session_id);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-500 transition-opacity focus:outline-none cursor-pointer"
                      title="删除会话"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  )}
                </span>
              </li>
            );
          })
        )}
      </ul>
    </div>
  );
}
