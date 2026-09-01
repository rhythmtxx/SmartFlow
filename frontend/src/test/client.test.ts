import { describe, expect, it, vi, beforeEach } from "vitest";
import { apiFetch, setToken } from "../api/client";

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
    const mock = vi
      .fn()
      .mockResolvedValue(new Response('{"detail":"Unauthorized"}', { status: 401 }));
    vi.stubGlobal("fetch", mock);
    const spy = vi.fn();
    window.addEventListener("smartflow:unauthorized", spy);
    await apiFetch("/api/status");
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
