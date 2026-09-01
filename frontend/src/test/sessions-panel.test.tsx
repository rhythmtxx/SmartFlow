import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AppProviders } from "../store";
import SessionsPanel from "../components/sidebar/SessionsPanel";

const ok = (body: unknown) => new Response(JSON.stringify(body), { status: 200 });

describe("SessionsPanel", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("渲染会话列表，当前会话高亮", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        ok({
          sessions: [
            { session_id: "default", message_count: 3, last_active: "2026-09-01" },
            { session_id: "abc12345", message_count: 0, last_active: null },
          ],
        })
      )
    );
    localStorage.setItem("smartflow_session_id", "abc12345");
    render(
      <AppProviders>
        <SessionsPanel />
      </AppProviders>
    );
    await waitFor(() => expect(screen.getByText(/abc12345/)).toBeInTheDocument());
    const item = screen.getByText(/abc12345/).closest("li")!;
    const dot = item.querySelector("span span")!; // 激活指示点（嵌套在 flex 包裹层内）
    expect(dot.className).toContain("bg-cyber-blue");
  });

  it("新建会话调用 POST /api/sessions", async () => {
    const mock = vi
      .fn()
      .mockResolvedValueOnce(ok({ sessions: [] })) // #1 挂载 refreshSessions
      .mockResolvedValueOnce(ok({ sessions: [] })) // #2 createSession 前置 refreshSessions
      .mockResolvedValueOnce(ok({ session_id: "new-1" })) // #3 POST /api/sessions
      .mockResolvedValueOnce(
        ok({ sessions: [{ session_id: "new-1", message_count: 0, last_active: null }] })
      ); // #4 后置 refreshSessions
    vi.stubGlobal("fetch", mock);
    render(
      <AppProviders>
        <SessionsPanel />
      </AppProviders>
    );
    fireEvent.click(screen.getByTitle("新建会话"));
    await waitFor(() =>
      expect(mock.mock.calls.some(([u, i]) => u === "/api/sessions" && i?.method === "POST")).toBe(
        true
      )
    );
  });
});
