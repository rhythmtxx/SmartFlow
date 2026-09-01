import { useEffect, useState } from "react";
import type { ApprovalRequired } from "../../store";

interface Props {
  pending: ApprovalRequired | null;
  onResolve: (approvalId: string, approved: boolean) => void;
}

const SECONDS = 60;

/** HITL 审批弹窗：60s 倒计时，超时自动拒绝（样式从 static/index.html 1176-1210 行迁移） */
export default function ApprovalDialog({ pending, onResolve }: Props) {
  const [remaining, setRemaining] = useState(SECONDS);

  // 倒计时
  useEffect(() => {
    if (!pending) return;
    setRemaining(SECONDS);
    const t = setInterval(() => setRemaining((r) => r - 1), 1000);
    return () => clearInterval(t);
  }, [pending]);

  // 归零时自动拒绝（remaining === 0 守卫保证只触发一次）
  useEffect(() => {
    if (pending && remaining === 0) {
      onResolve(pending.approval_id, false);
    }
  }, [remaining, pending, onResolve]);

  if (!pending) return null;

  return (
    <div
      style={{
        display: "flex",
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(0,0,0,0.85)",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "monospace",
      }}
    >
      <div
        style={{
          background: "#0a0a0c",
          border: "1px solid #00f0ff",
          borderRadius: 8,
          padding: 24,
          maxWidth: 480,
          width: "100%",
        }}
      >
        <div
          style={{
            color: "#00f0ff",
            fontSize: 11,
            letterSpacing: 2,
            textTransform: "uppercase",
            marginBottom: 12,
          }}
        >
          ⚠ Human Approval Required
        </div>
        <p style={{ color: "#a1a1aa", fontSize: 14, margin: "0 0 14px 0" }}>{pending.reason}</p>
        <div style={{ color: "#f4f4f5", fontSize: 14, marginBottom: 12 }}>{pending.name}</div>
        <pre
          style={{
            color: "#00f0ff",
            fontSize: 13,
            margin: 0,
            whiteSpace: "pre-wrap",
            wordBreak: "break-all",
            background: "#121214",
            border: "1px solid #2a2a30",
            borderRadius: 6,
            padding: 10,
            maxHeight: 200,
            overflowY: "auto",
          }}
        >
          {pending.arguments}
        </pre>
        <div style={{ color: "#71717a", fontSize: 12, textAlign: "right", margin: "16px 0" }}>
          {remaining} 秒后自动拒绝
        </div>
        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button
            onClick={() => onResolve(pending.approval_id, false)}
            style={{
              background: "transparent",
              border: "1px solid #52525b",
              color: "#a1a1aa",
              padding: "8px 16px",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            拒绝
          </button>
          <button
            onClick={() => onResolve(pending.approval_id, true)}
            style={{
              background: "#00f0ff",
              border: "none",
              color: "#050505",
              padding: "8px 16px",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            同意并执行
          </button>
        </div>
      </div>
    </div>
  );
}
