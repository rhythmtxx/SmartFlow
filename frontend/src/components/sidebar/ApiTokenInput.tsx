import { useEffect, useState } from "react";
import { useAuth } from "../../store";
import { apiFetch } from "../../api/client";

type Status = "idle" | "verifying" | "ok" | "error";

/** 保存后即时验证（旧 JS saveApiToken 的 React 版） */
async function verifyToken(): Promise<"ok" | "error"> {
  try {
    const res = await apiFetch("/api/status");
    return res.status === 401 ? "error" : "ok";
  } catch {
    return "error";
  }
}

export default function ApiTokenInput() {
  const { apiToken, setApiToken } = useAuth();
  const [value, setValue] = useState(apiToken);
  const [status, setStatus] = useState<Status>("idle");

  const save = async () => {
    const token = value.trim();
    setApiToken(token);
    if (!token) {
      setStatus("idle");
      return;
    }
    setStatus("verifying");
    setStatus(await verifyToken());
  };

  // 401 全局事件 → 提示 token 无效（旧 handleAuthError 文案）
  useEffect(() => {
    const onUnauthorized = () => setStatus("error");
    window.addEventListener("smartflow:unauthorized", onUnauthorized);
    return () => window.removeEventListener("smartflow:unauthorized", onUnauthorized);
  }, []);

  const text =
    status === "idle"
      ? apiToken
        ? "Token accepted — auth active."
        : "Not configured — auth disabled."
      : status === "verifying"
        ? "Token saved. Verifying access..."
        : status === "ok"
          ? "Token accepted — auth active."
          : "ERROR: 401 Unauthorized — 请检查 Token 是否正确。";
  const color =
    status === "error" ? "text-red-500" : status === "ok" ? "text-cyber-green" : status === "verifying" ? "text-cyber-blue" : "text-zinc-600";

  return (
    <div className="mt-6">
      <label
        htmlFor="api-token-input"
        className="text-[10px] uppercase font-bold tracking-widest text-zinc-500 mb-2 flex items-center"
      >
        <svg className="w-3 h-3 mr-2 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
          />
        </svg>
        API Token <span className="normal-case tracking-normal text-zinc-600 ml-1">(可选)</span>
      </label>
      <div className="flex gap-2">
        <input
          id="api-token-input"
          type="password"
          autoComplete="off"
          placeholder="SMARTFLOW_API_TOKEN"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          className="flex-1 min-w-0 bg-zinc-900 border border-zinc-700 focus:border-cyber-blue focus:outline-none px-2.5 py-2 text-[11px] font-mono text-cyber-blue rounded-sm transition-colors"
        />
        <button
          type="button"
          onClick={save}
          title="保存 Token"
          className="px-3 py-2 bg-zinc-900 border border-zinc-700 hover:border-cyber-green hover:text-cyber-green active:bg-zinc-800 focus:outline-none text-zinc-400 text-[10px] font-mono tracking-widest uppercase rounded-sm transition-all duration-300 flex-shrink-0"
        >
          SET
        </button>
      </div>
      <p id="api-token-status" className={`text-[10px] ${color} font-mono mt-1.5 leading-relaxed`}>
        {text}
      </p>
    </div>
  );
}
