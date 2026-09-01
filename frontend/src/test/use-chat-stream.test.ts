import { describe, expect, it } from "vitest";
import { feedStream } from "../hooks/useChatStream";

describe("feedStream（SSE 增量解析）", () => {
  it("完整事件解析并派发", () => {
    const { events, buffer } = feedStream(
      "",
      'data: {"type":"text_delta","content":"你"}\n\n' +
        'data: {"type":"text_delta","content":"好"}\n\n' +
        'data: {"type":"token_usage","prompt_tokens":10,"completion_tokens":5,"total_tokens":15}\n\n'
    );
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
