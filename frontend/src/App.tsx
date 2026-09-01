import { AppProviders, useChat, useSession } from "./store";
import { apiFetch } from "./api/client";
import SessionsPanel from "./components/sidebar/SessionsPanel";
import TelemetryPanel from "./components/sidebar/TelemetryPanel";
import ApiTokenInput from "./components/sidebar/ApiTokenInput";
import SkillsList from "./components/sidebar/SkillsList";
import ToolsList from "./components/sidebar/ToolsList";
import MemoryPanel from "./components/sidebar/MemoryPanel";
import OutputsPanel from "./components/sidebar/OutputsPanel";
import ChatContainer from "./components/chat/ChatContainer";
import ApprovalDialog from "./components/dialogs/ApprovalDialog";

/** HITL 审批宿主：pendingApproval 非空时弹窗；onResolve 提交 /api/approve（带 session）并关闭 */
function ApprovalDialogHost() {
  const { pendingApproval, setPendingApproval } = useChat();
  const { currentSession } = useSession();
  const resolve = async (id: string, approved: boolean) => {
    await apiFetch("/api/approve", {
      method: "POST",
      body: JSON.stringify({ approval_id: id, approved, session: currentSession }),
    });
    setPendingApproval(null);
  };
  return <ApprovalDialog pending={pendingApproval} onResolve={(id, a) => void resolve(id, a)} />;
}

export default function App() {
  return (
    <AppProviders>
      <div className="h-screen flex overflow-hidden selection:bg-cyber-blue selection:text-black">
        {/* Left HUD: Telemetry & Status */}
        <aside className="w-80 glass-panel flex flex-col h-full z-10 border-r border-cyber-border shadow-[5px_0_30px_rgba(0,0,0,0.5)]">
          {/* Header */}
          <div className="p-6 border-b border-cyber-border relative">
            <div className="flex items-center justify-between mb-1">
              <h1 className="text-2xl font-semibold tracking-wide text-white font-mono">SmartFlow</h1>
              <span className="flex h-3 w-3 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyber-green opacity-75" />
                <span className="relative inline-flex rounded-full h-3 w-3 bg-cyber-green shadow-[0_0_8px_#00ffa3]" />
              </span>
            </div>
            <p className="text-xs text-zinc-500 font-mono tracking-widest uppercase">System.Online // v1.1.0</p>
          </div>

          <SessionsPanel />
          <TelemetryPanel />
          <div className="p-6 border-b border-cyber-border">
            <ApiTokenInput />
          </div>
          <SkillsList />
          <ToolsList />
        </aside>

        {/* Main Interface */}
        <main className="flex-1 flex flex-col relative">
          <ChatContainer />
        </main>

        {/* Right HUD: Workspace & Memory */}
        <aside className="w-80 glass-panel flex flex-col h-full z-10 border-l border-cyber-border shadow-[-5px_0_30px_rgba(0,0,0,0.5)]">
          <MemoryPanel />
          <OutputsPanel />
        </aside>

        <ApprovalDialogHost />
      </div>
    </AppProviders>
  );
}
