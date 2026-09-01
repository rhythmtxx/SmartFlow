import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import MessageBubble from "../components/chat/MessageBubble";

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
