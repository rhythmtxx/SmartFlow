import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { AppProviders } from "../store";
import ApprovalDialog from "../components/dialogs/ApprovalDialog";
import type { ApprovalRequired } from "../store";

const approvalEvent: ApprovalRequired = {
  type: "approval_required",
  approval_id: "ap-1",
  id: "call-1",
  name: "http_post",
  arguments: '{"url":"https://example.com"}',
  risk_level: "high",
  reason: "高风险操作，执行前需要确认。",
};

describe("ApprovalDialog", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("渲染工具名/参数/原因，倒计时从 60 递减", () => {
    vi.useFakeTimers();
    render(
      <AppProviders>
        <ApprovalDialog pending={approvalEvent} onResolve={vi.fn()} />
      </AppProviders>
    );
    expect(screen.getByText("http_post")).toBeInTheDocument();
    expect(screen.getByText(/60/)).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(screen.getByText(/55/)).toBeInTheDocument();
  });

  it("同意回调 onResolve(approvalId, true)（父级负责 POST /api/approve）", async () => {
    const onResolve = vi.fn();
    render(
      <AppProviders>
        <ApprovalDialog pending={approvalEvent} onResolve={onResolve} />
      </AppProviders>
    );
    fireEvent.click(screen.getByText(/同意/));
    await act(async () => {
      await Promise.resolve();
    });
    expect(onResolve).toHaveBeenCalledWith("ap-1", true);
  });

  it("60s 超时自动拒绝 onResolve(approvalId, false)，且只回调一次", () => {
    vi.useFakeTimers();
    const onResolve = vi.fn();
    render(
      <AppProviders>
        <ApprovalDialog pending={approvalEvent} onResolve={onResolve} />
      </AppProviders>
    );
    act(() => {
      vi.advanceTimersByTime(60000);
    });
    expect(onResolve).toHaveBeenCalledWith("ap-1", false);
    expect(onResolve).toHaveBeenCalledTimes(1);
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(onResolve).toHaveBeenCalledTimes(1);
  });
});
