"""
评估集 Mock 用假组件（Fake LLM Client）。

复用 test_hitl.py 的思路，扩展为"脚本化"：按计划依次返回 tool_call，
最后一轮返回纯文本。用于零成本验证 Agent 的工具调用链是否正确。
"""
import json
from typing import List, Dict, Any


class FakeDelta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, delta):
        self.delta = delta


class FakeChunk:
    def __init__(self, delta):
        self.choices = [FakeChoice(delta)]
        self.usage = None


class FakeToolCall:
    def __init__(self, index, id, name, arguments):
        self.index = index
        self.id = id
        self.type = "function"
        self.function = type("F", (), {"name": name, "arguments": arguments})()


class FakeStream:
    """模拟一次 LLM 流式响应。"""
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        self._it = iter(self._chunks)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


class ScriptedClient:
    """
    脚本化 FakeClient：
    - 前 len(plan) 次调用按计划返回 tool_call（每轮一个工具）
    - 之后返回 final_reply 纯文本
    """
    def __init__(self, tool_sequence: List[Dict[str, Any]], final_reply: str = "处理完毕。"):
        self.tool_sequence = tool_sequence
        self.final_reply = final_reply
        self.call_count = 0
        self.chat = self
        self.completions = self

    async def create(self, **kwargs):
        self.call_count += 1
        idx = self.call_count - 1
        if idx < len(self.tool_sequence):
            step = self.tool_sequence[idx]
            tc = FakeToolCall(
                0,
                f"call_{self.call_count}",
                step["tool"],
                json.dumps(step.get("arguments", {}), ensure_ascii=False),
            )
            return FakeStream([FakeChunk(FakeDelta(tool_calls=[tc]))])
        # 最后返回纯文本
        return FakeStream([FakeChunk(FakeDelta(content=self.final_reply))])
