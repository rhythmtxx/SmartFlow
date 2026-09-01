import { describe, expect, it, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { AppProviders, useSession, useChat } from "../store";

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
    const mock = vi
      .fn()
      .mockResolvedValueOnce(ok({ sessions: [] })) // #1 createSession 前置 refreshSessions
      .mockResolvedValueOnce(ok({ session_id: "new-1" })) // #2 POST /api/sessions
      .mockResolvedValueOnce(
        ok({ sessions: [{ session_id: "new-1", message_count: 0, last_active: null }] })
      ); // #3 后置 refreshSessions
    vi.stubGlobal("fetch", mock);
    const { result } = renderHook(() => useSession(), { wrapper: AppProviders });
    await act(async () => {
      await result.current.createSession();
    });
    expect(mock.mock.calls.some(([u, i]) => u === "/api/sessions" && i.method === "POST")).toBe(
      true
    );
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
