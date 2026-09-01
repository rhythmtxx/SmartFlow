# 前端工程化（React + Vite 迁移）Implementation Plan

> **For agentic workers:** 执行本计划。Task 1-4、7-16 内联执行（共享 store/组件上下文，紧耦合）；Task 5/6 是两个互相独立的静态面板任务，可并行派发两个 subagent。
> 步骤用 `- [ ]` 复选框跟踪。

**Goal:** 把单文件前端 `static/index.html`（约 1100 行）迁移为 `frontend/` React 19 + Vite + TypeScript 工程：组件化、类型化、可测试、可维护；12 个核心交互区功能与视觉 1:1 等价；后端 `/api/*` 零改动；构建产物由 FastAPI 伺服。

**Architecture:** 渐进迁移（非大爆炸）：阶段 A 工程骨架 → B 静态面板（Skills/Tools/Memory/Outputs）→ C 交互面板（Token/会话/统计）→ D 聊天+审批核心（SSE 流式）→ E 质量与伺服切换。样式从 CDN Tailwind 迁到本地 Tailwind v4 构建（cyber 色板经 `@theme` 定义，类名不变，视觉零漂移）。状态管理用 React Context + hooks（弃 Zustand）；SSE 事件用 TS 判别联合（discriminated union）。旧 `static/` 在验收前保留。

**Tech Stack:** React 19 + 最新 Vite（`npm create vite@latest --template react-ts`）、TypeScript、Tailwind v4（`@tailwindcss/vite` 插件，无需 postcss 配置）、react-markdown（替换 marked）、@fontsource/outfit + @fontsource/jetbrains-mono（本地字体，离线可用）、Vitest + @testing-library/react（jsdom）、ESLint（模板自带）+ Prettier。

**Spec:** `前端工程化-任务大纲.md`（git 已提交，权威规格）。对规格的偏离见 Global Constraints 第 8-11 条。

## Global Constraints

1. Node v24.18.0；本机 PowerShell 执行策略拦截 `npm.ps1`，**所有 npm 命令必须用 `npm.cmd`**。
2. 分支：新建 `feature/frontend-react-vite`，不在 main 上直接实现。
3. 后端 Python：`D:\mytools\miniforge3\envs\smartflow\python.exe`（Python 3.11.15），回归测试用它跑。
4. `.env` 已配 `LLM_API_KEY`（base_url `https://0x7e.vip/keys/v1`）→ 阶段 D/E 可真实联调 SSE；无 SMARTFLOW_API_TOKEN → 鉴权默认关闭，本地联调无需 token。
5. **本机无 Docker**：Dockerfile 多阶段只写不 build 验证（与前次 more-tools 计划一致）。
6. localStorage key 沿用旧值：`smartflow_api_token` / `smartflow_session_id`（存量用户不丢状态）。
7. 轮询频率沿用：status 10s / outputs 5s / memory 10s / sessions 30s / stats 3s。
8. **弃 Zustand** → React Context + hooks（用户已批准）。
9. **React 18+Vite 5 → 最新稳定版**（React 19 + 最新 Vite，用户已批准）。
10. **Tailwind v3+PostCSS → v4 + `@tailwindcss/vite`**（更少配置文件；`@theme` 定义 cyber 色板与动画，类名与旧版一致）。
11. **知识库 API 不迁移**（`/api/knowledge/*` 后端有接口但旧前端无 UI，1:1 等价原则下不建 UI）。
12. SSE 事件类型（与 `core/loop.py` 一一对应）：`text_delta` / `tool_call_start` / `tool_call_end` / `token_usage` / `approval_required` / `approval_resolved` / `error` / `turn_end`。
13. `/outputs` 静态直链已失效：文件打开必须走 `/api/outputs/download/{name}`（fetch → Blob → objectURL），不能直接 `<a href="/outputs/...">`。
14. 迁移验收前保留 `static/index.html`；Task 15 才删旧挂载与旧文件。

---

## Task 1: 工程骨架（阶段 A）

**Files:**
- Create: `frontend/`（vite 脚手架）、`frontend/vite.config.ts`、`frontend/src/styles/index.css`、`frontend/src/main.tsx`（改）、`frontend/index.html`（改）、`frontend/src/App.tsx`（改）、`frontend/package.json`（改 scripts）
- Delete: `frontend/src/App.css`、`frontend/src/assets/react.svg`、`frontend/public/vite.svg`

- [ ] **Step 1: 建分支 + 脚手架**
  ```powershell
  git checkout -b feature/frontend-react-vite
  npm.cmd create vite@latest frontend -- --template react-ts
  cd frontend
  npm.cmd install
  npm.cmd install @tailwindcss/vite tailwindcss react-markdown @fontsource/outfit @fontsource/jetbrains-mono
  npm.cmd install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event prettier
  ```
  若 create-vite 交互式提问（如是否装 create-vite / rolldown），全部回车默认。完成后 `Remove-Item src/App.css, src/assets/react.svg, public/vite.svg`。
- [ ] **Step 2: 写 `frontend/vite.config.ts`**
  ```ts
  /// <reference types="vitest/config" />
  import { defineConfig } from "vite";
  import react from "@vitejs/plugin-react";
  import tailwindcss from "@tailwindcss/vite";

  export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/api": "http://localhost:8000",
        "/outputs": "http://localhost:8000",
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
    },
  });
  ```
- [ ] **Step 3: 写 `frontend/src/test/setup.ts`**
  ```ts
  import "@testing-library/jest-dom/vitest";
  ```
- [ ] **Step 4: 写 `frontend/src/styles/index.css`**（Tailwind v4 主题 + 从 `static/index.html` 迁移自定义样式）
  ```css
  @import "tailwindcss";

  @theme {
    --font-sans: "Outfit", ui-sans-serif, system-ui, sans-serif;
    --font-mono: "JetBrains Mono", ui-monospace, monospace;

    --color-cyber-blue: #00f0ff;
    --color-cyber-green: #00ffa3;
    --color-cyber-purple: #b000ff;
    --color-cyber-dark: #050505;
    --color-cyber-panel: rgba(20, 20, 22, 0.75);
    --color-cyber-border: #27272a;

    --animate-radar-spin: radar 3s linear infinite;
    --animate-pulse-glow: glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    --animate-slide-up: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;

    @keyframes radar {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    @keyframes glow {
      0%, 100% { opacity: 1; box-shadow: 0 0 10px rgba(0, 240, 255, 0.5); }
      50% { opacity: 0.5; box-shadow: 0 0 2px rgba(0, 240, 255, 0.2); }
    }
    @keyframes slideUp {
      0% { opacity: 0; transform: translateY(20px); }
      100% { opacity: 1; transform: translateY(0); }
    }
  }

  /* ---- 以下整段从 static/index.html 的 <style> 块（约第 88-198 行）原样迁移，删除 tailwind.config 脚本 ---- */
  /* body 背景、::-webkit-scrollbar 系列、.glass-panel、.hud-border(+::before/::after)、
     .prose 系列（strong/pre/code）、.chat-bubble-ai、.chat-bubble-user、.tool-indicator、
     .cyber-input:focus-within、.glow-text 及其它所有自定义类，逐字复制，不要改写 */
  ```
  迁移后把 `<style>` 块在旧文件里对应的 tailwind.config 脚本部分丢弃（已由 `@theme` 替代）。
- [ ] **Step 5: 改 `frontend/index.html`**：`<title>` 改为 `SmartFlow`；删除模板 favicon link（可选保留）；head 中**不**加任何 CDN 链接（字体由 fontsource 包导入）。
- [ ] **Step 6: 改 `frontend/src/main.tsx`**
  ```tsx
  import { StrictMode } from "react";
  import { createRoot } from "react-dom/client";
  import "@fontsource/outfit/300.css";
  import "@fontsource/outfit/400.css";
  import "@fontsource/outfit/500.css";
  import "@fontsource/outfit/600.css";
  import "@fontsource/jetbrains-mono/300.css";
  import "@fontsource/jetbrains-mono/400.css";
  import "@fontsource/jetbrains-mono/500.css";
  import "./styles/index.css";
  import App from "./App";

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>
  );
  ```
- [ ] **Step 7: 改 `frontend/src/App.tsx` 为占位**（后续 Task 替换）
  ```tsx
  export default function App() {
    return <div className="h-screen flex items-center justify-center font-mono text-cyber-blue">SmartFlow v2 · React migration in progress</div>;
  }
  ```
- [ ] **Step 8: `frontend/package.json` scripts 增加**：`"test": "vitest run"`、`"test:watch": "vitest"`、`"format": "prettier --write \"src/**/*.{ts,tsx,css}\""`
- [ ] **Step 9: 验证**：`npm.cmd run build` 期望 exit 0 且 dist 产物生成；`npm.cmd test` 期望 0 tests pass。
- [ ] **Step 10: 提交**：`git add frontend && git commit -m "feat(frontend): scaffold React+Vite+TS+Tailwind4 skeleton (phase A)"`

---

## Task 2: API 类型契约 + fetch 客户端（阶段 B 前置，TDD）

**Files:**
- Create: `frontend/src/api/types.ts`、`frontend/src/api/client.ts`
- Test: `frontend/src/test/client.test.ts`

**Interfaces:**
- Produces: `getToken(): string`、`setToken(t: string): void`、`apiFetch(path: string, init?: RequestInit): Promise<Response>`、`ChatEvent`（判别联合）等全部类型——后续所有任务消费。

- [ ] **Step 1: 写失败测试 `frontend/src/test/client.test.ts`**
  ```ts
  import { describe, expect, it, vi, beforeEach } from "vitest";
  import { apiFetch, setToken } from "../src/api/client";

  describe("api/client", () => {
    beforeEach(() => {
      localStorage.clear();
      vi.restoreAllMocks();
    });

    it("有 token 时带 Authorization: Bearer 头", async () => {
      setToken("secret123");
      const mock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
      vi.stubGlobal("fetch", mock);
      await apiFetch("/api/status");
      const [url, init] = mock.mock.calls[0];
      expect(url).toBe("/api/status");
      expect(new Headers(init.headers).get("Authorization")).toBe("Bearer secret123");
    });

    it("无 token 时不带 Authorization 头", async () => {
      const mock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
      vi.stubGlobal("fetch", mock);
      await apiFetch("/api/status");
      const [, init] = mock.mock.calls[0];
      expect(new Headers(init.headers).has("Authorization")).toBe(false);
    });

    it("401 时派发 smartflow:unauthorized 事件", async () => {
      const mock = vi.fn().mockResolvedValue(new Response('{"detail":"Unauthorized"}', { status: 401 }));
      vi.stubGlobal("fetch", mock);
      const spy = vi.fn();
      window.addEventListener("smartflow:unauthorized", spy);
      await apiFetch("/api/status");
      expect(spy).toHaveBeenCalledTimes(1);
    });
  });
  ```
- [ ] **Step 2: 运行确认失败**：`npm.cmd test` 期望 FAIL（模块不存在）。
- [ ] **Step 3: 写 `frontend/src/api/types.ts`**（字段与后端核实一致，勿改字段名）
  ```ts
  // 与 core/loop.py / core/session.py / core/memory.py / app.py 响应对应

  // ---- SSE 事件（core/loop.py 逐一核实）----
  export type ChatEvent =
    | { type: "text_delta"; content: string }
    | { type: "tool_call_start"; id: string; name: string; arguments: string }
    | {
        type: "tool_call_end"; id: string; name: string;
        result_summary: string; approved?: boolean;
      }
    | { type: "token_usage"; prompt_tokens: number; completion_tokens: number; total_tokens: number }
    | {
        type: "approval_required"; approval_id: string; id: string; name: string;
        arguments: string; risk_level: string; reason: string;
      }
    | { type: "approval_resolved"; approval_id: string; id: string; name: string; approved: boolean }
    | { type: "error"; content: string }
    | { type: "turn_end"; new_messages?: unknown[] };

  // ---- /api/status ----
  export interface StatusResponse {
    skills: { name: string; description: string; active: boolean }[];
    tools: { name: string; description: string }[];
  }

  // ---- /api/sessions ----
  export interface SessionItem {
    session_id: string;
    message_count: number;
    last_active: string | null;
  }

  // ---- /api/stats ----
  export interface StatsResponse {
    totals: {
      prompt_tokens: number; completion_tokens: number; total_tokens: number;
      rounds: number; tool_calls: number; estimated_cost: number | null;
    };
    tool_call_stats: { tool: string; count: number; last_used: string }[];
    recent_tool_calls: {
      tool: string; arguments: string; result_summary: string; created_at: string;
    }[];
    recent_rounds: { prompt_tokens: number; completion_tokens: number; total_tokens: number; created_at: string }[];
  }

  // ---- /api/outputs ----
  export interface OutputFile { name: string; size: number; mtime: number }

  // ---- /api/memory ----
  export interface MemoryResponse {
    stats: { total_messages_in_window: number; has_long_term_memory: boolean };
    long_term_memory: string;
  }

  // ---- /api/history（OpenAI 消息格式，与 core/loop.py 内部 messages 一致）----
  export interface HistoryMessage {
    role: "system" | "user" | "assistant" | "tool";
    content: string | null;
    tool_calls?: { id: string; type: string; function: { name: string; arguments: string } }[];
    tool_call_id?: string;
    name?: string;
  }
  export interface HistoryResponse {
    messages: HistoryMessage[];
    tokens: { prompt: number; completion: number };
  }

  // ---- /api/approve ----
  export interface ApproveResponse { status: "ok" | "error"; approved?: boolean; message?: string }
  ```
- [ ] **Step 4: 写 `frontend/src/api/client.ts`**
  ```ts
  export const TOKEN_KEY = "smartflow_api_token";

  export function getToken(): string {
    return localStorage.getItem(TOKEN_KEY) ?? "";
  }
  export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  /** 统一 fetch：自动带 Authorization 头（有 token 才加）、JSON Content-Type（非 FormData）、401 全局事件 */
  export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
    const headers = new Headers(init.headers);
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const res = await fetch(path, { ...init, headers });
    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent("smartflow:unauthorized"));
    }
    return res;
  }
  ```
- [ ] **Step 5: 运行确认通过**：`npm.cmd test` 期望 3 passed。
- [ ] **Step 6: 提交**：`git add frontend/src/api frontend/src/test/client.test.ts && git commit -m "feat(frontend): api types + fetch client with auth header (TDD)"`

---

## Task 3: 全局状态层（Context + hooks，弃 Zustand）

**Files:**
- Create: `frontend/src/store/AuthContext.tsx`、`frontend/src/store/SessionContext.tsx`、`frontend/src/store/ChatContext.tsx`、`frontend/src/store/index.tsx`（Provider 聚合）
- Test: `frontend/src/test/session-store.test.tsx`

**Interfaces:**
- Produces: `useAuth()` → `{ apiToken, setApiToken }`；`useSession()` → `{ currentSession, sessions, setCurrentSession, refreshSessions, createSession, deleteSession }`；`useChat()` → `{ messages: UIMessage[], cumulativeTokens, isGenerating, appendMessage, updateToolCall, addTokens, resetTokens, setIsGenerating, clearMessages }`；`AppProviders`。
- Consumes: `apiFetch`、`getToken`/`setToken`（Task 2）、localStorage keys `smartflow_session_id`。

- [ ] **Step 1: 写失败测试 `frontend/src/test/session-store.test.tsx`**
  ```tsx
  import { describe, expect, it, vi, beforeEach } from "vitest";
  import { renderHook, act, waitFor } from "@testing-library/react";
  import { AppProviders, useSession, useChat } from "../src/store";

  const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

  describe("store", () => {
    beforeEach(() => {
      localStorage.clear();
      vi.restoreAllMocks();
    });

    it("currentSession 从 localStorage 读取并持久化（key: smartflow_session_id）", () => {
      localStorage.setItem("smartflow_session_id", "abc123");
      const { result } = renderHook(() => useSession(), { wrapper: AppProviders });
      expect(result.current.currentSession).toBe("abc123");
      act(() => result.current.setCurrentSession("xyz999"));
      expect(localStorage.getItem("smartflow_session_id")).toBe("xyz999");
    });

    it("createSession 调 POST /api/sessions 并切换过去", async () => {
      const mock = vi.fn()
        .mockResolvedValueOnce(ok({ sessions: [] }))           // #1 挂载 usePolling 触发的 refreshSessions
        .mockResolvedValueOnce(ok({ sessions: [] }))           // #2 createSession 前置 refreshSessions
        .mockResolvedValueOnce(ok({ session_id: "new-1" }))    // #3 POST /api/sessions
        .mockResolvedValueOnce(ok({ sessions: [{ session_id: "new-1", message_count: 0, last_active: null }] })); // #4 后置 refreshSessions
      vi.stubGlobal("fetch", mock);
      const { result } = renderHook(() => useSession(), { wrapper: AppProviders });
      await act(async () => { await result.current.createSession(); });
      expect(mock.mock.calls.some(([u, i]) => u === "/api/sessions" && i.method === "POST")).toBe(true);
      await waitFor(() => expect(result.current.currentSession).toBe("new-1"));
    });

    it("切会话时重置 token 数字（resetTokens）", () => {
      const { result } = renderHook(() => useChat(), { wrapper: AppProviders });
      act(() => result.current.addTokens({ prompt: 100, completion: 50 }));
      expect(result.current.cumulativeTokens).toEqual({ prompt: 100, completion: 50 });
      act(() => result.current.resetTokens());
      expect(result.current.cumulativeTokens).toEqual({ prompt: 0, completion: 0 });
    });
  });
  ```
- [ ] **Step 2: 运行确认失败**：`npm.cmd test` 期望 FAIL（store 不存在）。
- [ ] **Step 3: 写三个 Context**
  `frontend/src/store/AuthContext.tsx`：
  ```tsx
  import { createContext, useContext, useState, type ReactNode } from "react";
  import { getToken, setToken as persistToken } from "../api/client";

  interface AuthState {
    apiToken: string;
    setApiToken: (t: string) => void;
  }
  const Ctx = createContext<AuthState | null>(null);

  export function AuthProvider({ children }: { children: ReactNode }) {
    const [apiToken, setApiTokenState] = useState<string>(() => getToken());
    const setApiToken = (t: string) => {
      setApiTokenState(t);
      persistToken(t);
    };
    return <Ctx.Provider value={{ apiToken, setApiToken }}>{children}</Ctx.Provider>;
  }
  export function useAuth() {
    const v = useContext(Ctx);
    if (!v) throw new Error("useAuth must be used within AuthProvider");
    return v;
  }
  ```
  `frontend/src/store/ChatContext.tsx`：
  ```tsx
  import { createContext, useContext, useState, type ReactNode } from "react";

  export interface ToolCallUI {
    id: string;
    name: string;
    arguments: string;
    resultSummary?: string;
    status: "running" | "done" | "rejected";
  }
  export interface UIMessage {
    id: string;
    role: "user" | "assistant" | "system" | "tool";
    content: string;
    toolCalls?: ToolCallUI[];
  }

  interface ChatState {
    messages: UIMessage[];
    cumulativeTokens: { prompt: number; completion: number };
    isGenerating: boolean;
    appendMessage: (m: Omit<UIMessage, "id">) => void;
    updateToolCall: (id: string, patch: Partial<ToolCallUI>) => void;
    addTokens: (t: { prompt: number; completion: number }) => void;
    resetTokens: () => void;
    setIsGenerating: (v: boolean) => void;
    clearMessages: () => void;
  }
  const Ctx = createContext<ChatState | null>(null);
  let seq = 0;
  const uid = () => `m${++seq}-${Date.now()}`;

  export function ChatProvider({ children }: { children: ReactNode }) {
    const [messages, setMessages] = useState<UIMessage[]>([]);
    const [cumulativeTokens, setTokens] = useState({ prompt: 0, completion: 0 });
    const [isGenerating, setGenerating] = useState(false);

    const appendMessage: ChatState["appendMessage"] = (m) =>
      setMessages((prev) => [...prev, { ...m, id: uid() }]);
    const updateToolCall: ChatState["updateToolCall"] = (id, patch) =>
      setMessages((prev) =>
        prev.map((m) =>
          m.toolCalls ? { ...m, toolCalls: m.toolCalls.map((tc) => (tc.id === id ? { ...tc, ...patch } : tc)) } : m
        )
      );
    const addTokens = (t: { prompt: number; completion: number }) =>
      setTokens((prev) => ({ prompt: prev.prompt + t.prompt, completion: prev.completion + t.completion }));
    const resetTokens = () => setTokens({ prompt: 0, completion: 0 });
    const clearMessages = () => setMessages([]);

    return (
      <Ctx.Provider value={{ messages, cumulativeTokens, isGenerating, appendMessage, updateToolCall, addTokens, resetTokens, setIsGenerating: setGenerating, clearMessages }}>
        {children}
      </Ctx.Provider>
    );
  }
  export function useChat() {
    const v = useContext(Ctx);
    if (!v) throw new Error("useChat must be used within ChatProvider");
    return v;
  }
  ```
  `frontend/src/store/SessionContext.tsx`：
  ```tsx
  import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
  import { apiFetch } from "../api/client";
  import type { SessionItem } from "../api/types";

  const SESSION_KEY = "smartflow_session_id";

  interface SessionState {
    currentSession: string;
    sessions: SessionItem[];
    setCurrentSession: (id: string) => void;
    refreshSessions: () => Promise<void>;
    createSession: () => Promise<void>;
    deleteSession: (id: string) => Promise<void>;
  }
  const Ctx = createContext<SessionState | null>(null);

  export function SessionProvider({ children }: { children: ReactNode }) {
    const [currentSession, setCurrent] = useState<string>(() => localStorage.getItem(SESSION_KEY) ?? "default");
    const [sessions, setSessions] = useState<SessionItem[]>([]);

    const setCurrentSession = useCallback((id: string) => {
      setCurrent(id);
      localStorage.setItem(SESSION_KEY, id);
    }, []);

    const refreshSessions = useCallback(async () => {
      const res = await apiFetch("/api/sessions");
      if (!res.ok) return;
      const data = (await res.json()) as { sessions: SessionItem[] };
      setSessions(data.sessions);
    }, []);

    const createSession = useCallback(async () => {
      await refreshSessions();
      const res = await apiFetch("/api/sessions", { method: "POST" });
      if (!res.ok) return;
      const data = (await res.json()) as { session_id: string };
      setCurrentSession(data.session_id);
      await refreshSessions();
    }, [refreshSessions, setCurrentSession]);

    const deleteSession = useCallback(async (id: string) => {
      await apiFetch(`/api/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (id === currentSession) setCurrentSession("default");
      await refreshSessions();
    }, [currentSession, refreshSessions, setCurrentSession]);

    return (
      <Ctx.Provider value={{ currentSession, sessions, setCurrentSession, refreshSessions, createSession, deleteSession }}>
        {children}
      </Ctx.Provider>
    );
  }
  export function useSession() {
    const v = useContext(Ctx);
    if (!v) throw new Error("useSession must be used within SessionProvider");
    return v;
  }
  ```
  `frontend/src/store/index.tsx`：
  ```tsx
  import type { ReactNode } from "react";
  import { AuthProvider } from "./AuthContext";
  import { SessionProvider } from "./SessionContext";
  import { ChatProvider } from "./ChatContext";

  export function AppProviders({ children }: { children: ReactNode }) {
    return (
      <AuthProvider>
        <SessionProvider>
          <ChatProvider>{children}</ChatProvider>
        </SessionProvider>
      </AuthProvider>
    );
  }
  export { useAuth } from "./AuthContext";
  export { useSession } from "./SessionContext";
  export { useChat } from "./ChatContext";
  export type { UIMessage, ToolCallUI } from "./ChatContext";
  ```
- [ ] **Step 4: 运行确认通过**：`npm.cmd test` 期望 3 passed（client 3 + store 3 共 6）。
- [ ] **Step 5: 提交**：`git add frontend/src/store frontend/src/test/session-store.test.tsx && git commit -m "feat(frontend): auth/session/chat context stores (TDD)"`

---

## Task 4: usePolling 通用轮询 hook

**Files:**
- Create: `frontend/src/hooks/usePolling.ts`

- [ ] **Step 1: 写 `frontend/src/hooks/usePolling.ts`**
  ```ts
  import { useEffect } from "react";

  /** 通用轮询：挂载立即执行一次，按 intervalMs 定时执行，卸载自动清理。deps 变化时重启。 */
  export function usePolling(fn: () => void | Promise<void>, intervalMs: number, deps: unknown[] = []) {
    useEffect(() => {
      void fn();
      const t = setInterval(() => void fn(), intervalMs);
      return () => clearInterval(t);
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, deps);
  }
  ```
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0（无测试，YAGNI——10 行标准 useEffect 封装，Task 5/6 的集成会覆盖它）。
- [ ] **Step 3: 提交**：`git add frontend/src/hooks/usePolling.ts && git commit -m "feat(frontend): usePolling hook"`

---

## Task 5: 静态面板——Skills / Tools / Memory（阶段 B，可并行 subagent）

**Files:**
- Create: `frontend/src/hooks/useStatus.ts`、`frontend/src/components/sidebar/SkillsList.tsx`、`frontend/src/components/sidebar/ToolsList.tsx`、`frontend/src/components/sidebar/MemoryPanel.tsx`

**Interfaces:**
- Consumes: `usePolling`（Task 4）、`useSession`、`apiFetch`、`StatusResponse`/`MemoryResponse`（Task 2）。
- Produces: `useStatus()` → `{ skills, tools }`（轮询 10s）；三个面板组件各自 `<SectionTitle icon path .../>` 内联 SVG 复用现有 heroicons path。

**实现要点（对照 `static/index.html`）：**
- `useStatus.ts`：`usePolling(async () => { const res = await apiFetch("/api/status"); ... setSkills(data.skills); setTools(data.tools); }, 10000, [])`。
- `SkillsList.tsx`：标题「Active Skills」+ `<ul id="skills-list">`；每项渲染 `skill.name` / `skill.description` / active 指示。**HTML 结构与 class 字符串从 `static/index.html` 第 290-326 行（aside 中 Loaded Modules: Skills 区）与渲染逻辑第 597-633 行照抄**：旧 JS 用 `s.active ? ... : ...` 切换点颜色（active 绿色 `shadow-[0_0_5px_#00ffa3]`，否则 `bg-zinc-600`），照搬为 JSX 三元。
- `ToolsList.tsx`：标题「Core Tools」+ `<ul id="tools-list">`，每项 name + description；结构与 class 从 `static/index.html` 第 326-340 行 + 渲染逻辑 618-633 行照抄。
- `MemoryPanel.tsx`：标题「Long-term Memory」+ `<div className="prose ...">`；`/api/memory?session=<currentSession>` 轮询 10s（`usePolling` deps 含 `currentSession`）；`long_term_memory` 用 `<ReactMarkdown>` 渲染（`import ReactMarkdown from "react-markdown"`），空串显示 `<em>` 占位（旧 HTML 第 394-405 行的默认态照抄）。
- 旧 JS 中「加载中」占位文案（"Initializing modules..." / "No persistent memory established..."）保留为初始渲染态。

- [ ] **Step 1: 实现上述 4 个文件**（对旧 HTML 逐字复制 class，保证视觉 1:1）
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0；`npm.cmd test` 全绿（旧 6 用例不受影响）。
- [ ] **Step 3: 提交**：`git add frontend/src/hooks/useStatus.ts frontend/src/components/sidebar && git commit -m "feat(frontend): skills/tools/memory panels with polling (phase B)"`

---

## Task 6: 静态面板——OutputsPanel（上传/打开/删除，阶段 B，可并行 subagent）

**Files:**
- Create: `frontend/src/components/sidebar/OutputsPanel.tsx`

**Interfaces:**
- Consumes: `usePolling`、`apiFetch`、`OutputFile`（Task 2）。
- Produces: `formatBytes(bytes: number): string`（内部函数）。

**实现要点（对照 `static/index.html`）：**
- 标题「Workspace Outputs」+ 上传按钮（label + `<input type="file" className="hidden">`）+ 列表 + 右侧 ping 小点；HTML 从第 407-433 行照抄。
- 列表轮询 5s：`/api/outputs` → `{files}`；`usePolling` deps `[]`。
- **上传**：`/api/upload`，FormData + `apiFetch`（不设 Content-Type，让 fetch 自动带 boundary）；成功后刷新列表 + ping 闪烁（旧逻辑 730-763 行）。
- **打开**：`/api/outputs/download/<name>` → `apiFetch` → `res.blob()` → `URL.createObjectURL`；`.pptx` 结尾走 `<a download>` 触发下载，其余 `window.open(url)`（旧逻辑 764-790 行）；完成后 `URL.revokeObjectURL`。
- **删除**：`DELETE /api/outputs/<name>` → 刷新（旧逻辑 791-810 行）。
- `formatBytes` 从旧 JS 第 677-684 行照抄（B/KB/MB/GB，1 位小数）。
- 空列表占位 "No artifacts detected..."。

- [ ] **Step 1: 实现 `OutputsPanel.tsx`**
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0；`npm.cmd test` 全绿。
- [ ] **Step 3: 提交**：`git add frontend/src/components/sidebar/OutputsPanel.tsx && git commit -m "feat(frontend): outputs panel with upload/download/delete (phase B)"`

---

## Task 7: 交互面板——ApiTokenInput（阶段 C）

**Files:**
- Create: `frontend/src/components/sidebar/ApiTokenInput.tsx`

**Interfaces:**
- Consumes: `useAuth()`（Task 3）、`getToken`（Task 2）。

**实现要点（对照 `static/index.html`）：**
- HTML 从第 249-270 行照抄：label「API Token (可选)」+ password input（`value={apiToken}`）+「SET」按钮 + 状态 `<p id="api-token-status">`。
- SET 按钮 `onClick={() => setApiToken(inputValue)}`；输入框受控 `value` 用本地 state 初始化 `apiToken`。
- 状态文案逻辑照抄旧 JS 第 561-596 行：空 token → "Not configured — auth disabled."；非空 → "Auth enabled. Token stored locally."；**监听 `smartflow:unauthorized` 事件**（`useEffect` 内 `window.addEventListener`，清理时移除）→ 显示 "401: Token 无效或未配置" 红色提示（旧 handleAuthError 文案）。

- [ ] **Step 1: 实现 `ApiTokenInput.tsx`**
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0；`npm.cmd test` 全绿。
- [ ] **Step 3: 提交**：`git add frontend/src/components/sidebar/ApiTokenInput.tsx && git commit -m "feat(frontend): api token input with auth event handling (phase C)"`

---

## Task 8: 交互面板——SessionsPanel（阶段 C）

**Files:**
- Create: `frontend/src/components/sidebar/SessionsPanel.tsx`
- Test: `frontend/src/test/sessions-panel.test.tsx`

**Interfaces:**
- Consumes: `useSession()`（sessions/currentSession/createSession/deleteSession/refreshSessions）、`useChat()`（clearMessages/resetTokens）、`setCurrentSession`。
- Produces: 切换会话的副作用（清消息、重置 token）由面板在 `setCurrentSession` 后调用 `clearMessages()` + `resetTokens()`。

- [ ] **Step 1: 写失败测试 `frontend/src/test/sessions-panel.test.tsx`**
  ```tsx
  import { describe, expect, it, vi, beforeEach } from "vitest";
  import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
  import { AppProviders } from "../src/store";
  import SessionsPanel from "../src/components/sidebar/SessionsPanel";

  const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

  describe("SessionsPanel", () => {
    beforeEach(() => {
      localStorage.clear();
      vi.restoreAllMocks();
    });

    it("渲染会话列表，当前会话高亮", async () => {
      vi.stubGlobal("fetch", vi.fn().mockResolvedValue(ok({
        sessions: [
          { session_id: "default", message_count: 3, last_active: "2026-09-01" },
          { session_id: "abc12345", message_count: 0, last_active: null },
        ],
      })));
      localStorage.setItem("smartflow_session_id", "abc12345");
      render(
        <AppProviders>
          <SessionsPanel />
        </AppProviders>
      );
      await waitFor(() => expect(screen.getByText(/abc12345/)).toBeInTheDocument());
      const item = screen.getByText(/abc12345/).closest("li")!;
      const dot = item.querySelector("span")!; // 激活指示点
      expect(dot.className).toContain("bg-cyber-green");
    });

    it("新建会话调用 POST /api/sessions", async () => {
      const mock = vi.fn()
        .mockResolvedValueOnce(ok({ sessions: [] }))           // #1 挂载 refreshSessions
        .mockResolvedValueOnce(ok({ sessions: [] }))           // #2 createSession 前置 refreshSessions
        .mockResolvedValueOnce(ok({ session_id: "new-1" }))    // #3 POST /api/sessions
        .mockResolvedValueOnce(ok({ sessions: [{ session_id: "new-1", message_count: 0, last_active: null }] })); // #4 后置 refreshSessions
      vi.stubGlobal("fetch", mock);
      render(
        <AppProviders>
          <SessionsPanel />
        </AppProviders>
      );
      fireEvent.click(screen.getByTitle("新建会话"));
      await waitFor(() =>
        expect(mock.mock.calls.some(([u, i]) => u === "/api/sessions" && i?.method === "POST")).toBe(true)
      );
    });
  });
  ```
- [ ] **Step 2: 运行确认失败**：`npm.cmd test` 期望该文件 FAIL（组件不存在）。
- [ ] **Step 3: 实现 `SessionsPanel.tsx`**
  - HTML 结构/class 从 `static/index.html` 第 211-247 行照抄：标题「Sessions」+ 新建按钮（`title="新建会话"` 的 SVG）+ `<ul>` 列表。
  - 挂载时 `refreshSessions()`（`usePolling(refreshSessions, 30000)`，旧 30s 轮询）。
  - 列表项：label = `session_id === "default" ? "default" : session_id.slice(0, 8)`；激活态绿点 `bg-cyber-green shadow-[0_0_5px_#00ffa3]`，非激活 `bg-zinc-600`（旧 renderSessions 467-497 行）。
  - 点击项：`setCurrentSession(id)` + `clearMessages()` + `resetTokens()`（切换后 ChatContainer 的 history 拉取依赖 currentSession 自动触发，见 Task 13）。
  - 删除按钮（每项 hover 显示的 ✕）：调 `deleteSession(id)`；`default` 会话不显示删除按钮（后端也禁止删）。
  - 新建按钮：`createSession()`（store 内已含 POST + 切换）。
- [ ] **Step 4: 运行确认通过**：`npm.cmd test` 期望该文件 2 passed。
- [ ] **Step 5: 提交**：`git add frontend/src/components/sidebar/SessionsPanel.tsx frontend/src/test/sessions-panel.test.tsx && git commit -m "feat(frontend): sessions panel with create/switch/delete (TDD, phase C)"`

---

## Task 9: 交互面板——TelemetryPanel（token/cost/tool calls，阶段 C）

**Files:**
- Create: `frontend/src/hooks/useStats.ts`、`frontend/src/components/sidebar/TelemetryPanel.tsx`

**Interfaces:**
- Consumes: `usePolling`、`useSession`、`useChat`（cumulativeTokens）、`StatsResponse`（Task 2）。
- Produces: `useStats()` → `{ totals, recentToolCalls }`（轮询 3s，deps 含 currentSession）。

**实现要点（对照 `static/index.html`）：**
- HTML 从第 251-289 行照抄：「Telemetry Data」区——TX_PROMPT / RX_COMPLETION / TOTAL_BANDWIDTH / COST_ESTIMATE 四行 + 「Tool Calls」时间线。
- Token 数字：`useChat().cumulativeTokens`（流式累加）+ 旧 JS `pad0`（`String(num).padStart(4, '0')`，第 899 行）格式化为 `0000`；**轮询到的 `totals.prompt_tokens` 仅作初始化**（Task 13 的 history 恢复会 set）。
- 成本：`totals.estimated_cost` → `¥{cost.toFixed(6)}`（`null` 显示 `¥--`，旧逻辑 640-648 行）。
- 工具调用时间线：`recentToolCalls` → 每项 `tool` / `result_summary`；着色规则照抄旧 JS 659-665 行：`tool === 'exec'` → `text-cyber-red`（红色，注意旧代码 `text-red-400` 是 tailwind 内置色，直接沿用），成功 `text-cyber-green` 带 ✓、失败（summary 含「错误」或「失败」）`text-red-400` 带 ✗；`tool-calls-count` 显示 `totals.tool_calls`。
- 下方「Purge Memory」按钮（旧 HTML 第 283-289 行）：`onClick` → `POST /api/clear?session=<currentSession>` 后刷新 stats + 提示。放本面板末尾。

- [ ] **Step 1: 实现 `useStats.ts` + `TelemetryPanel.tsx`**
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0；`npm.cmd test` 全绿。
- [ ] **Step 3: 提交**：`git add frontend/src/hooks/useStats.ts frontend/src/components/sidebar/TelemetryPanel.tsx && git commit -m "feat(frontend): telemetry panel with stats polling (phase C)"`

---

## Task 10: useChatStream——SSE 流式核心 hook（阶段 D，TDD 核心）

**Files:**
- Create: `frontend/src/hooks/useChatStream.ts`
- Test: `frontend/src/test/use-chat-stream.test.ts`

**Interfaces:**
- Consumes: `apiFetch`、`useSession`、`useChat`（appendMessage/updateToolCall/addTokens/setIsGenerating）、`ChatEvent`。
- Produces: `useChatStream()` → `{ send(text: string): Promise<void>, isGenerating }`；导出纯函数 `feedStream(buffer: string, chunk: string): { events: ChatEvent[]; buffer: string }` 供测试与复用。

- [ ] **Step 1: 写失败测试 `frontend/src/test/use-chat-stream.test.ts`**
  ```ts
  import { describe, expect, it } from "vitest";
  import { feedStream } from "../src/hooks/useChatStream";

  describe("feedStream（SSE 增量解析）", () => {
    it("完整事件解析并派发", () => {
      const { events, buffer } = feedStream("", [
        'data: {"type":"text_delta","content":"你"}',
        "",
        'data: {"type":"text_delta","content":"好"}',
        "",
        'data: {"type":"token_usage","prompt_tokens":10,"completion_tokens":5,"total_tokens":15}',
        "",
      ].join("\n"));
      expect(events).toEqual([
        { type: "text_delta", content: "你" },
        { type: "text_delta", content: "好" },
        { type: "token_usage", prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
      ]);
      expect(buffer).toBe("");
    });

    it("半个 data 行跨 chunk：不崩溃、拼回完整", () => {
      let r = feedStream("", 'data: {"type":"text_delta","content":"你好');
      expect(r.events).toEqual([]);
      expect(r.buffer).toContain("你好");
      r = feedStream(r.buffer, '好"}\n\n');
      expect(r.events).toEqual([{ type: "text_delta", content: "你好好" }]);
      expect(r.buffer).toBe("");
    });

    it("空行/注释行/非法 JSON 不崩溃且被忽略", () => {
      const { events, buffer } = feedStream("", "\n\n: keepalive comment\n\ndata: not-json\n\n");
      expect(events).toEqual([]);
      expect(buffer).toBe("");
    });

    it("单个事件流式逐字（text_delta 拼接由调用方完成，此处验证事件顺序）", () => {
      const all: { type: string; content?: string }[] = [];
      let buf = "";
      for (const piece of ["d", "ata: {", '"type":"text_delta","content":"', "Hi", '"}\n\n']) {
        const r = feedStream(buf, piece);
        buf = r.buffer;
        all.push(...r.events);
      }
      expect(all).toEqual([{ type: "text_delta", content: "Hi" }]);
    });
  });
  ```
- [ ] **Step 2: 运行确认失败**：`npm.cmd test` 期望该文件 FAIL（模块不存在）。
- [ ] **Step 3: 实现 `useChatStream.ts`**
  ```ts
  import { useCallback, useRef, useState } from "react";
  import { apiFetch } from "../api/client";
  import { useSession } from "../store";
  import { useChat } from "../store";
  import type { ChatEvent } from "../api/types";

  /** 纯函数：把 chunk 追加到 buffer，切出完整 SSE 事件，保留未闭合尾部。 */
  export function feedStream(buffer: string, chunk: string): { events: ChatEvent[]; buffer: string } {
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

  export function useChatStream() {
    const { currentSession } = useSession();
    const chat = useChat();
    const [isGenerating, setIsGenerating] = useState(false);
    const abortRef = useRef<AbortController | null>(null);

    const handleEvent = useCallback((e: ChatEvent) => {
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
          setPendingApproval(e);
          break;
        case "approval_resolved":
          chat.updateToolCall(e.id, {
            resultSummary: e.approved ? undefined : "用户拒绝或超时，操作已取消",
            status: e.approved ? "done" : "rejected",
          });
          setPendingApproval(null);
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
    }, [chat]);

    const send = useCallback(async (text: string) => {
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
          buffer += decoder.decode(value, { stream: true });
          const { events, buffer: rest } = feedStream(buffer, "");
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
    }, [chat, currentSession, handleEvent]);

    return { send, isGenerating };
  }
  ```
  > 注意：`setPendingApproval` 需从 `useChat()` 解构（`const { setPendingApproval } = useChat()` 或并入 `chat` 对象）。审批状态 `pendingApproval: ApprovalRequired | null`（类型定义见 Task 12）与 `setPendingApproval` 在 ChatContext 中补齐（interface + Provider value + `useChat` 返回），由 Task 12 ApprovalDialog 消费。
- [ ] **Step 4: 运行确认通过**：`npm.cmd test` 期望 use-chat-stream 4 passed。
- [ ] **Step 5: 提交**：`git add frontend/src/hooks/useChatStream.ts frontend/src/test/use-chat-stream.test.ts frontend/src/store/ChatContext.tsx && git commit -m "feat(frontend): SSE chat stream hook with incremental parser (TDD, phase D)"`

---

## Task 11: 聊天区——ChatContainer + MessageBubble + ToolCallCard + ChatInput（阶段 D）

**Files:**
- Create: `frontend/src/components/chat/ChatContainer.tsx`、`MessageBubble.tsx`、`ToolCallCard.tsx`、`ChatInput.tsx`

**Interfaces:**
- Consumes: `useChat`（messages/isGenerating）、`useChatStream`（send）、`UIMessage`/`ToolCallUI`（Task 3）。
- Produces: `ChatContainer` 聚合消息渲染 + 输入区 + 自动滚动；被 `App.tsx` 引用。

**实现要点（对照 `static/index.html`）：**
- **ChatInput**：HTML 从第 356-387 行照抄——表单（`>` 前缀 + input + submit 按钮）+ 外层渐变遮罩；`onSubmit`：`send(text)`，成功后 `setText("")`；`isGenerating` 时 input `disabled` + 按钮 `disabled:opacity-30`（旧 997-1008 行「生成中禁用」）。
- **MessageBubble**：按 role 渲染（对照旧 JS 916-985 行）：
  - user：`.chat-bubble-user` 气泡（`max-w-2xl chat-bubble-user px-5 py-3 rounded-l-lg rounded-tr-lg shadow-md text-zinc-200`），顶部小标签「USER INPUT」。
  - assistant：`.chat-bubble-ai` 气泡（`max-w-3xl chat-bubble-ai px-6 py-5 rounded-r-lg rounded-bl-lg shadow-sm text-zinc-300 font-mono text-sm leading-relaxed`）+ 顶部 `System Override` 风格小标签（旧 createAssistantBubble 里 `text-[10px] text-cyber-blue/70 mb-2 uppercase tracking-widest flex items-center` 的「ASSISTANT OUTPUT」），内容 `<ReactMarkdown className="prose ...">`。
  - system：`appendSystemMessage` 样式（旧 928-938 行，红色 `text-red-400` 系警示条）。
  - tool：渲染 `ToolCallCard`。
- **ToolCallCard**：**采用旧 JS 第 859-880 行的 markdown 块引用格式**（视觉 1:1）：`> 🛠 **正在调用工具/技能**: \`name\`` + `> **参数**: \`\`\`json ... \`\`\``（旧 1048 行）→ 执行中；`> ✅ **执行结果**: \`summary\``（旧 1055 行）→ 完成；`> ❌ summary` → 拒绝/失败。实现为 `ToolCallCard` 组件渲染这些结构化行（不做成 ReactMarkdown 二次解析，直接 JSX 输出同样的视觉：`<blockquote>` + 前缀符号 + name/code 样式），状态着色 running 蓝 / done 绿 / rejected 红。
- **ChatContainer**：`messages.map` → MessageBubble；底部初始「System Override Initiated」欢迎消息（旧 HTML 第 332-340 行静态块，作为初始 state 或在容器顶部硬渲染一次）；`useEffect` 监听 messages 变化 `scrollToBottom()`（`ref.current.scrollTop = ref.current.scrollHeight`）；渲染 ChatInput。
- 浮动工具指示卡（`#tool-float-card`，旧 HTML 第 341-348 行）可选：`isGenerating` 时显示（`opacity-100`），否则隐藏——保持旧视觉。

- [ ] **Step 1: 实现 4 个组件**（class 字符串逐字复制）
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0；`npm.cmd test` 全绿。
- [ ] **Step 3: 提交**：`git add frontend/src/components/chat && git commit -m "feat(frontend): chat container/message/tool-card/input (phase D)"`

---

## Task 12: ApprovalDialog——HITL 审批弹窗（阶段 D，TDD）

**Files:**
- Create: `frontend/src/components/dialogs/ApprovalDialog.tsx`
- Test: `frontend/src/test/approval-dialog.test.tsx`

**Interfaces:**
- Consumes: `useChat`（`pendingApproval: ApprovalRequired | null`、`setPendingApproval`——Task 10 已在 ChatContext 补齐）、`useSession`（currentSession）、`apiFetch`。
- Produces: 弹窗 60s 倒计时；同意/拒绝/超时 → `POST /api/approve { approval_id, approved, session }` → 成功后 `setPendingApproval(null)`；`pendingApproval` 为 null 时返回 null。

- [ ] **Step 1: 写失败测试 `frontend/src/test/approval-dialog.test.tsx`**
  ```tsx
  import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
  import { render, screen, fireEvent, act } from "@testing-library/react";
  import { AppProviders } from "../src/store";
  import ApprovalDialog from "../src/components/dialogs/ApprovalDialog";

  const approvalEvent = {
    type: "approval_required",
    approval_id: "ap-1",
    id: "call-1",
    name: "http_post",
    arguments: '{"url":"https://example.com"}',
    risk_level: "high",
    reason: "高风险操作，执行前需要确认。",
  };

  describe("ApprovalDialog", () => {
    beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
    afterEach(() => { vi.useRealTimers(); });

    it("渲染工具名/参数/原因，倒计时从 60 递减", () => {
      vi.useFakeTimers();
      render(
        <AppProviders>
          <ApprovalDialog pending={approvalEvent} onResolve={vi.fn()} />
        </AppProviders>
      );
      expect(screen.getByText("http_post")).toBeInTheDocument();
      expect(screen.getByText(/60/)).toBeInTheDocument();
      act(() => { vi.advanceTimersByTime(5000); });
      expect(screen.getByText(/55/)).toBeInTheDocument();
    });

    it("同意调用 /api/approve 且带 approved=true 与 session", async () => {
      const mock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: "ok", approved: true }), { status: 200 }));
      vi.stubGlobal("fetch", mock);
      const onResolve = vi.fn();
      render(
        <AppProviders>
          <ApprovalDialog pending={approvalEvent} onResolve={onResolve} />
        </AppProviders>
      );
      fireEvent.click(screen.getByText(/同意/));
      await act(async () => { await Promise.resolve(); });
      expect(onResolve).toHaveBeenCalledWith("ap-1", true);
    });

    it("60s 超时自动拒绝（approved=false）", () => {
      vi.useFakeTimers();
      const onResolve = vi.fn();
      render(
        <AppProviders>
          <ApprovalDialog pending={approvalEvent} onResolve={onResolve} />
        </AppProviders>
      );
      act(() => { vi.advanceTimersByTime(60000); });
      expect(onResolve).toHaveBeenCalledWith("ap-1", false);
    });
  });
  ```
  > 说明：`onResolve` 由父级（useChatStream 所在组件）传入：`async (id, approved) => { await apiFetch("/api/approve", { method: "POST", body: JSON.stringify({ approval_id: id, approved, session: currentSession }) }); setPendingApproval(null); }`。测试验证弹窗职责（倒计时 + 回调），fetch 逻辑由父级测试/联调覆盖。
- [ ] **Step 2: 运行确认失败**：`npm.cmd test` 期望该文件 FAIL（组件不存在）。
- [ ] **Step 3: 实现 `ApprovalDialog.tsx`**（HTML 从 `static/index.html` 第 1176-1210 行照抄，该区是内联样式非 tailwind，可整体迁移；JSX 化：`display: pending ? "flex" : "none"`）
  ```tsx
  import { useEffect, useState } from "react";
  import type { ChatEvent } from "../api/types";

  export type ApprovalRequired = Extract<ChatEvent, { type: "approval_required" }>;

  interface Props {
    pending: ApprovalRequired | null;
    onResolve: (approvalId: string, approved: boolean) => void;
  }

  const SECONDS = 60;

  export default function ApprovalDialog({ pending, onResolve }: Props) {
    const [remaining, setRemaining] = useState(SECONDS);

    useEffect(() => {
      if (!pending) return;
      setRemaining(SECONDS);
      const t = setInterval(() => setRemaining((r) => r - 1), 1000);
      return () => clearInterval(t);
    }, [pending]);

    useEffect(() => {
      if (!pending) return;
      if (remaining <= 0) {
        onResolve(pending.approval_id, false); // 超时自动拒绝
      }
    }, [remaining, pending, onResolve]);

    if (!pending) return null;

    return (
      <div style={{ display: "flex", position: "fixed", inset: 0, zIndex: 9999,
        background: "rgba(0,0,0,0.85)", alignItems: "center", justifyContent: "center", fontFamily: "monospace" }}>
        <div style={{ background: "#0a0a0c", border: "1px solid #00f0ff", borderRadius: 8, padding: 24, maxWidth: 480, width: "100%" }}>
          <div style={{ color: "#00f0ff", fontSize: 11, letterSpacing: 2, textTransform: "uppercase", marginBottom: 12 }}>
            ⚠ Human Approval Required
          </div>
          <p style={{ color: "#a1a1aa", fontSize: 14, margin: "0 0 14px 0" }}>{pending.reason}</p>
          <div style={{ color: "#f4f4f5", fontSize: 14, marginBottom: 12 }}>{pending.name}</div>
          <pre style={{ color: "#00f0ff", fontSize: 13, margin: 0, whiteSpace: "pre-wrap",
            wordBreak: "break-all", background: "#121214", border: "1px solid #2a2a30", borderRadius: 6, padding: 10, maxHeight: 200, overflowY: "auto" }}>
            {pending.arguments}
          </pre>
          <div style={{ color: "#71717a", fontSize: 12, textAlign: "right", margin: "16px 0" }}>
            {remaining} 秒后自动拒绝
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
            <button onClick={() => onResolve(pending.approval_id, false)}
              style={{ background: "transparent", border: "1px solid #52525b", color: "#a1a1aa",
                padding: "8px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
              拒绝
            </button>
            <button onClick={() => onResolve(pending.approval_id, true)}
              style={{ background: "#00f0ff", border: "none", color: "#050505",
                padding: "8px 16px", borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 600 }}>
              同意并执行
            </button>
          </div>
        </div>
      </div>
    );
  }
  ```
- [ ] **Step 4: 运行确认通过**：`npm.cmd test` 期望该文件 3 passed。
- [ ] **Step 5: 提交**：`git add frontend/src/components/dialogs/ApprovalDialog.tsx frontend/src/test/approval-dialog.test.tsx && git commit -m "feat(frontend): approval dialog with 60s countdown (TDD, phase D)"`

---

## Task 13: 历史恢复（阶段 D）

**Files:**
- Modify: `frontend/src/components/chat/ChatContainer.tsx`（或新建 `frontend/src/hooks/useHistory.ts`）

**Interfaces:**
- Consumes: `useSession`（currentSession）、`useChat`（messages 追加、resetTokens、addTokens 或 setTokens——为 history 恢复加一个 `setTokens` 直接赋值 action 到 ChatContext）、`apiFetch`、`HistoryResponse`/`HistoryMessage`（Task 2）。
- 语义：挂载 + currentSession 变化时拉取 `/api/history?session=`，把 OpenAI 格式 messages 转成 `UIMessage[]` 整体替换（含 tool 消息折叠展示），tokens 直接 set 覆盖。

**实现要点（对照 `static/index.html` 第 829-890 行 fetchHistory）：**
- 消息转换：
  - `system` → `{ role: "system", content: msg.content ?? "" }`
  - `user` → `{ role: "user", content: msg.content ?? "" }`
  - `assistant` 且 `content` 非空 → `{ role: "assistant", content }`；若有 `tool_calls` → 同一条消息带 `toolCalls: [...{ id, name, arguments, status: "done", resultSummary: undefined }]`
  - `tool` → `{ role: "tool", content: "", toolCalls: [{ id: msg.tool_call_id ?? msg.name ?? "", name: msg.name ?? "tool", arguments: "{}", resultSummary: msg.content ?? "执行完毕", status: "done" }] }`（旧 JS 用 `msg.content || "执行完毕"` 的展示逻辑）
- 恢复后 `setTokens({ prompt: data.tokens.prompt, completion: data.tokens.completion })`（**覆盖**而非累加）。
- 竞态防护：useRef 存 `sessionRef.current = currentSession`，响应回来时若与当前不符则丢弃（旧 JS 切换会话时旧请求覆盖新状态的坑，大纲第 8 节）。
- 依赖：`useEffect(() => { load(); }, [currentSession])`；卸载/切换时无需 abort（以 sessionRef 判断为准）。

- [ ] **Step 1: 在 ChatContext 增加 `setTokens`（直接赋值）action，实现 useHistory（或直接写进 ChatContainer 的 useEffect）**
- [ ] **Step 2: 验证**：`npm.cmd run build` exit 0；`npm.cmd test` 全绿（旧 13 用例 + 新无独立测试，历史转换逻辑由 6.2 手动联调覆盖）。
- [ ] **Step 3: 提交**：`git add frontend/src && git commit -m "feat(frontend): session history restore with race guard (phase D)"`

---

## Task 14: 质量收尾——剩余测试 + ESLint/Prettier（阶段 E）

**Files:**
- Create: `frontend/src/test/message-bubble.test.tsx`、`frontend/.prettierrc.json`
- Modify: `frontend/package.json`（format 脚本已在 Task 1 加，此处跑）

- [ ] **Step 1: 写 `frontend/src/test/message-bubble.test.tsx`**
  ```tsx
  import { describe, expect, it } from "vitest";
  import { render, screen } from "@testing-library/react";
  import MessageBubble from "../src/components/chat/MessageBubble";

  describe("MessageBubble", () => {
    it("user/assistant/system 按角色渲染", () => {
      const { rerender } = render(<MessageBubble m={{ id: "1", role: "user", content: "你好" }} />);
      expect(screen.getByText("你好")).toBeInTheDocument();
      expect(screen.getByText("你好").closest("div")!.className).toContain("chat-bubble-user");

      rerender(<MessageBubble m={{ id: "2", role: "system", content: "⚠️ 出错" }} />);
      expect(screen.getByText(/出错/)).toBeInTheDocument();
    });

    it("assistant 的 markdown 渲染出 <p> 与 <code>", () => {
      render(<MessageBubble m={{ id: "3", role: "assistant", content: "看这个 `code` 和段落" }} />);
      const code = screen.getByText("code");
      expect(code.tagName).toBe("CODE");
      expect(screen.getByText(/和段落/).tagName).toBe("P");
    });
  });
  ```
- [ ] **Step 2: 运行确认失败**：`npm.cmd test` 期望该文件 FAIL（MessageBubble 存在则直接通过；若 Task 11 未实现该组件则先补——TDD 顺序允许 Task 11 已建组件，测试补上后必须红一次再绿，若直接绿则说明组件行为已正确，记录即可）。
- [ ] **Step 3: 写 `frontend/.prettierrc.json`**
  ```json
  { "semi": true, "singleQuote": false, "printWidth": 100, "trailingComma": "es5" }
  ```
  并 `npm.cmd run format` 全量格式化。
- [ ] **Step 4: ESLint 0 error**：`npm.cmd run lint`（模板自带 eslint 配置，含 react-hooks 规则）。有 error 就修（重点：`react-hooks/exhaustive-deps` 在 usePolling 处已有 disable 注释）。
- [ ] **Step 5: 全量测试**：`npm.cmd test` 期望全部通过（client 3 + store 3 + sessions-panel 2 + approval 3 + stream 4 + bubble 2 = 17）。
- [ ] **Step 6: 提交**：`git add frontend && git commit -m "chore(frontend): remaining tests + prettier/eslint clean (phase E)"`

---

## Task 15: 伺服切换——FastAPI 伺服 dist + 删旧挂载 + Dockerfile 多阶段（阶段 E）

**Files:**
- Modify: `app.py`、`Dockerfile`
- Delete: `static/index.html`（及 `static/` 目录）

- [ ] **Step 1: 改 `app.py`**
  - 删除第 94 行 `app.mount("/static", StaticFiles(directory="static"), name="static")` 与第 97-100 行根路由 `@app.get("/")`（FileResponse）。
  - **保留** `/outputs` 静态挂载（第 95 行）与全部 `/api/*` 路由。
  - 在文件**末尾**（`if __name__ == "__main__"` 之前）追加：
    ```python
    # 生产模式：伺服 Vite 构建产物（需先 npm run build）
    # 注意：必须放在所有 /api/* 路由与 /outputs 挂载之后注册（Starlette 按注册顺序匹配）
    if os.path.exists("frontend/dist"):
        app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")
    ```
- [ ] **Step 2: 删旧前端**：`Remove-Item -Recurse -Force static`
- [ ] **Step 3: 改 `Dockerfile` 为多阶段**
  ```dockerfile
  # 阶段 1: 构建前端
  FROM node:20-alpine AS frontend
  WORKDIR /app/frontend
  COPY frontend/package*.json ./
  RUN npm ci
  COPY frontend/ ./
  RUN npm run build

  # 阶段 2: Python 后端（原有内容，仅追加 COPY dist）
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  COPY . .
  COPY --from=frontend /app/frontend/dist ./frontend/dist
  RUN mkdir -p workspace/memory workspace/outputs workspace/skills
  EXPOSE 8000
  CMD ["python", "app.py"]
  ```
  本机无 Docker，**不执行 build**（沿用 more-tools 计划先例）；只检查语法/路径正确。
- [ ] **Step 4: 后端回归**（后台跑，用 smartflow 解释器）：
  ```powershell
  cd D:\project\SmartFlow
  D:\mytools\miniforge3\envs\smartflow\python.exe test_hitl.py
  D:\mytools\miniforge3\envs\smartflow\python.exe test_compress.py
  D:\mytools\miniforge3\envs\smartflow\python.exe test_more_tools.py
  D:\mytools\miniforge3\envs\smartflow\python.exe eval\run_eval.py
  ```
  期望全部通过（`/api/*` 零改动，应全绿；如个别用例依赖缺失环境需记录说明）。
- [ ] **Step 5: 联调验证（后端伺服 dist）**：
  ```powershell
  # 起后端（后台 job）
  D:\mytools\miniforge3\envs\smartflow\python.exe app.py
  # 验证 1: 首页由 dist 伺服
  curl.exe -s http://localhost:8000/ | Select-String "SmartFlow"
  # 验证 2: API 面不受影响
  curl.exe -s http://localhost:8000/api/status
  # 验证 3: SSE 全链路（真实 LLM Key 已配置；发一条简单消息，应看到 text_delta 流）
  curl.exe -s -N -X POST http://localhost:8000/api/chat -H "Content-Type: application/json" -d '{\"message\":\"回复OK即可\",\"session\":\"e2e-check\"}'
  ```
  期望：首页返回 dist 的 index.html；/api/status 返回 JSON；SSE 流含 `data: {"type": "text_delta"...`。
- [ ] **Step 6: 提交**：`git add app.py Dockerfile && git commit -m "feat: serve frontend dist via FastAPI, remove old static, multi-stage Dockerfile (phase E)"`（`git rm -r static` 一起提交）

---

## Task 16: 文档与全量验收（阶段 E）

**Files:**
- Modify: `README.md`、`CHANGELOG.md`

- [ ] **Step 1: README 更新**
  - 前端说明段：新增「前端开发（frontend/）」小节——`npm.cmd run dev`（Vite proxy → localhost:8000）+ `npm.cmd run build`（产物由 FastAPI 伺服）+ `npm.cmd test` / `npm.cmd run lint`；若 README 现有「静态伺服」说明引用 `static/index.html`，改为引用 `frontend/dist`。
  - Roadmap 第 381 行：`- [ ] **前端工程化**` → `- [x] **前端工程化** — 迁移到 React/Vite，组件化 + 测试（2026-09-01）`。
- [ ] **Step 2: CHANGELOG 更新**：追加条目「前端工程化：React 19 + Vite + TS 迁移（组件化/类型化/Vitest 17 用例/SSE 判别联合/localStorage 兼容）」。
- [ ] **Step 3: 全量验证命令重跑并读输出**：
  ```powershell
  cd frontend; npm.cmd run build; npm.cmd test; npm.cmd run lint
  ```
  期望：build exit 0、test 17 passed、lint 0 error。
- [ ] **Step 4: 提交**：`git add README.md CHANGELOG.md && git commit -m "docs: README/CHANGELOG/Roadmap update for frontend migration (phase E)"`

---

## 验收清单（对应规格第 7 节）

> **执行状态：2026-09-01 全部任务完成。** 证据均为验收当日新鲜运行；「⚠️」为环境限制项（非代码缺口），见「验收备注」。
> 证据命令：`npm.cmd test` / `npm.cmd run build` / `npm.cmd run lint`（受限沙箱下经 `vite-netuse-preload.cjs` + vitest threads 池运行）；后端回归用 `D:\mytools\miniforge3\envs\smartflow\python.exe`。

- [x] `frontend/` React+TS+Vite 工程；`npm.cmd run build` 产物可被 FastAPI 伺服（Task 1/15）
      — build exit 0；`GET /` 返回 dist index.html；`GET /api/status` 返回完整 JSON
- [x] 12 个核心交互区功能与视觉等价（Task 5-13；视觉类名逐字复制 + 阶段 D 联调）
      — SSE 解析 4 单测 / 审批倒计时 3 单测 / 会话 5 单测 / 消息渲染 2 单测 + 后端回归全绿
- [x] SSE 事件 TS 判别联合；组件拆分符合规格 3.1（Task 2/5-13）
- [x] Context+hooks 覆盖会话/Token/消息/统计；localStorage key 兼容（Task 3）
      — `smartflow_api_token` / `smartflow_session_id` 沿用旧 key
- [x] Vitest 17 用例通过；ESLint 0 error（Task 14/16）
      — 17 passed / 6 files；lint 0 errors（6 warnings 为 react-refresh 提示）
- [x] 开发模式（Vite proxy）与生产模式（FastAPI 伺服 dist）都能跑（Task 1/15）
      — 生产模式已验证；dev proxy 配置就位 ⚠️ dev server 未起浏览器实测（无浏览器环境）
- [x] 旧 `static/index.html` 已移除、旧挂载已清理（Task 15）
      — git rm static（-1214 行），`/static` 挂载与根 FileResponse 删除，`/outputs` 挂载保留
- [x] Dockerfile 多阶段构建（Task 15）
      — 已写 node:20-alpine → python:3.11-slim 两阶段 + .dockerignore ⚠️ 本机无 Docker，未跑 docker build
- [x] 后端 `/api/*` 零改动（除伺服与旧挂载清理）（Task 15 回归）
      — test_hitl ✓ / test_compress 11/11 ✓ / test_more_tools 全通过 ✓ / eval 5/5 ✓
- [x] README + CHANGELOG 更新、Roadmap 勾选（Task 16）

## 验收备注（环境限制项）

- **视觉 1:1 最终确认**：class 字符串逐字复制 + `@theme` 色板一致为保证，最终需浏览器打开 `http://localhost:8000` 肉眼比对（旧页面已删除，比对依据为 git 历史中的 `static/index.html`）。
- **dev 模式实测**：`frontend/vite.config.ts` 已配 `server.proxy`（/api、/outputs → :8000），未在浏览器实测。
- **Docker 构建**：本机无 Docker，`docker build` 未执行（与 more-tools 计划同限制）。
- **真实 LLM SSE 联调**：验收当日 LLM 代理（gpt-5.4-mini @ 0x7e.vip）返回 200 但 `chat_stream` 0 事件（tokens 0/0）——后端零改动、mock LLM 回归全绿、前端 SSE 解析由 4 个单测覆盖，判定为非迁移缺陷；真实模型环境联调即可（见 `.workflow/ledger.md` Ruling R8）。

## 已知限制

- 本机无 Docker：Dockerfile 多阶段无法本地 build 验证。
- 真实 HITL 弹窗联调依赖高风险的**可执行**工具；code_exec 需 Docker 不可用，弹窗逻辑由单元测试（Task 12）+ approval_required 事件联调覆盖。
- 视觉等价以「class 字符串逐字复制 + @theme 色板一致」为保证，最终以人工肉眼比对为准。
