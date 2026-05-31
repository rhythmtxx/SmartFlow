"""
HITL 人工审批功能 - 后端逻辑测试
不依赖真实大模型 API：用 FakeStream 模拟 LLM 的流式返回。

测试两条核心路径：
  1. 用户同意 -> 高风险工具被执行
  2. 用户拒绝 -> 工具被跳过，模型收到“被拒绝”消息

运行： python test_hitl.py
"""
import asyncio
from core.tools import ToolRegistry, ApprovalManager
from core.loop import AgentLoop


# ---- 用假的流式响应模拟大模型 ----
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
    """模拟一次 LLM 流式响应。第一轮返回 tool_call，第二轮返回纯文本。"""
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


class FakeClient:
    """模拟 AsyncOpenAI 客户端。按调用次数返回不同的流。"""
    def __init__(self):
        self.call_count = 0
        self.chat = self
        self.completions = self

    async def create(self, **kwargs):
        self.call_count += 1
        if self.call_count == 1:
            # 第一轮：模型决定调用 exec 工具（高风险）
            tc = FakeToolCall(0, "call_001", "exec", '{"command": "echo hello"}')
            return FakeStream([FakeChunk(FakeDelta(tool_calls=[tc]))])
        else:
            # 第二轮：模型根据工具结果给出最终回复
            return FakeStream([FakeChunk(FakeDelta(content="好的，已经处理完毕。"))])


async def run_one_case(approve_decision: bool):
    """跑一次完整对话，模拟用户做出 approve_decision 的审批决定。"""
    print(f"\n{'='*50}")
    print(f"测试场景：用户将选择 {'【同意】' if approve_decision else '【拒绝】'}")
    print('='*50)

    client = FakeClient()
    registry = ToolRegistry()
    approval_mgr = ApprovalManager()
    loop = AgentLoop(client, registry, approval_manager=approval_mgr, approval_timeout=10)

    messages = [{"role": "user", "content": "帮我执行 echo hello"}]

    tool_executed = False  # 记录工具是否真的被执行

    # “模拟用户”协程：收到审批请求后自动提交决定
    async def consume():
        nonlocal tool_executed
        async for event in loop.run(messages):
            etype = event["type"]
            if etype == "approval_required":
                print(f"  [前端] 收到审批请求: 工具={event['name']} 命令={event['arguments']}")
                # 模拟用户思考 0.2 秒后点击
                await asyncio.sleep(0.2)
                approval_mgr.resolve(event["approval_id"], approve_decision)
                print(f"  [用户] 已提交决定: {'同意' if approve_decision else '拒绝'}")
            elif etype == "approval_resolved":
                print(f"  [前端] 审批结果已确认: approved={event['approved']}")
            elif etype == "tool_call_end":
                print(f"  [工具] 执行结束: {event['result_summary']}")
                if "拒绝" not in event["result_summary"]:
                    tool_executed = True
            elif etype == "text_delta":
                print(f"  [模型] {event['content']}")

    await consume()

    print(f"\n  >>> 结果验证：工具实际执行 = {tool_executed}")
    expected = approve_decision
    status = "通过 ✓" if tool_executed == expected else "失败 ✗"
    print(f"  >>> 期望执行={expected}, 实际执行={tool_executed} -> 测试{status}")
    return tool_executed == expected


async def main():
    r1 = await run_one_case(approve_decision=True)
    r2 = await run_one_case(approve_decision=False)
    print(f"\n{'='*50}")
    print(f"总结: 同意路径={'通过' if r1 else '失败'}, 拒绝路径={'通过' if r2 else '失败'}")
    print('='*50)


if __name__ == "__main__":
    asyncio.run(main())
