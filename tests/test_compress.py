"""
上下文压缩功能测试
不依赖真实大模型 API：单元测试直测 MemoryStore 数据层，
集成测试用 FakeClient 模拟流式对话 + 非流式摘要调用。

运行： python test_compress.py
"""
import asyncio
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.memory import MemoryStore
from core.agent import TinyAgent
from core.skills import SkillsLoader
from core.tools import ToolRegistry
from eval.fakes import FakeStream, FakeChunk, FakeDelta


# ---------------------------------------------------------------------- #
# 工具函数                                                                  #
# ---------------------------------------------------------------------- #

# 工作区内的临时目录（沙箱内可写，且已被 .gitignore 的 _test_*/ 覆盖）
TMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_compress_tmp")
_tmp_counter = [0]


def _tmp() -> str:
    _tmp_counter[0] += 1
    return os.path.join(TMP_DIR, f"t{_tmp_counter[0]}")


def new_memory() -> MemoryStore:
    """独立的临时工作区，每个测试一个。"""
    return MemoryStore(_tmp(), session_id="t")


def seed(mem: MemoryStore, rounds: int, with_tools: bool = False):
    """预置完整轮次：user→assistant（可选 user→assistant(tc)→tool→assistant）。"""
    for i in range(rounds):
        mem.add_message({"role": "user", "content": f"问题{i}"})
        if with_tools:
            mem.add_message({
                "role": "assistant", "content": None,
                "tool_calls": [{"id": f"c{i}", "type": "function",
                                "function": {"name": "read_file", "arguments": "{}"}}]
            })
            mem.add_message({"role": "tool", "tool_call_id": f"c{i}",
                             "name": "read_file", "content": "文件内容"})
            mem.add_message({"role": "assistant", "content": f"回答{i}"})
        else:
            mem.add_message({"role": "assistant", "content": f"回答{i}"})


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})})()]


class CompressFakeClient:
    """流式对话返回固定文本；非流式调用（摘要）返回固定摘要或抛异常。"""
    def __init__(self, summary="这是压缩后的早期对话摘要。", fail_summary=False):
        self.chat = self
        self.completions = self
        self.summary = summary
        self.fail_summary = fail_summary
        self.summary_calls = 0

    async def create(self, **kwargs):
        if kwargs.get("stream"):
            return FakeStream([FakeChunk(FakeDelta(content="好的，我明白了。"))])
        self.summary_calls += 1
        if self.fail_summary:
            raise RuntimeError("摘要模型调用失败")
        return _Resp(self.summary)


def make_agent(ws, client):
    return TinyAgent(ws, session_id="t", shared={
        "client": client,
        "skills": SkillsLoader(ws),
        "knowledge": None,
        "tools": ToolRegistry(),
    })


# ---------------------------------------------------------------------- #
# 单元测试：MemoryStore 数据层                                              #
# ---------------------------------------------------------------------- #

def test_candidates_simple_rounds():
    mem = new_memory()
    seed(mem, 5)  # 10 条，全部是完整轮次
    cands = mem.get_compress_candidates()
    assert len(cands) == 10, f"应返回 10 条候选，实际 {len(cands)}"
    assert cands[0]["role"] == "user", "候选应从 user 开始"
    assert cands[-1]["role"] == "assistant", "候选应以 assistant 结束"


def test_candidates_tool_chain_included():
    mem = new_memory()
    seed(mem, 1, with_tools=True)  # 4 条
    seed(mem, 4)                    # +8 条，共 12 条
    cands = mem.get_compress_candidates()
    assert len(cands) == 10, f"应返回 10 条候选，实际 {len(cands)}"
    roles = [c["role"] for c in cands]
    assert roles[:4] == ["user", "assistant", "tool", "assistant"], \
        f"工具轮次应整轮进入候选: {roles}"
    assert "tool_calls" not in cands[-1], "候选末尾必须是 final assistant（无 tool_calls）"


def test_candidates_incomplete_tool_round_rejected():
    mem = new_memory()
    mem.add_message({"role": "user", "content": "q"})
    mem.add_message({
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"}}]
    })
    mem.add_message({"role": "tool", "tool_call_id": "c1", "name": "read_file", "content": "文件内容"})
    assert mem.get_compress_candidates() == [], "未闭环的工具轮次不应被压缩"


def test_candidates_ends_at_final_assistant_not_tool():
    """候选截止到 final assistant；剩余历史必须以 user 开头，不能留孤儿 tool。"""
    mem = new_memory()
    mem.add_message({"role": "user", "content": "q1"})
    mem.add_message({
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "c1", "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"}}]
    })
    mem.add_message({"role": "tool", "tool_call_id": "c1", "name": "read_file", "content": "文件内容"})
    mem.add_message({"role": "assistant", "content": "回答1"})  # final assistant
    mem.add_message({"role": "user", "content": "q2"})
    mem.add_message({
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "c2", "type": "function",
                        "function": {"name": "read_file", "arguments": "{}"}}]
    })
    mem.add_message({"role": "tool", "tool_call_id": "c2", "name": "read_file", "content": "文件内容"})

    cands = mem.get_compress_candidates()
    assert len(cands) == 4, f"候选应只含第一轮 4 条，实际 {len(cands)}"

    mem.delete_messages_by_ids([c["id"] for c in cands])
    remaining = mem.get_messages()
    assert remaining and remaining[0]["role"] == "user", \
        f"删除后剩余历史必须以 user 开头，实际开头: {remaining[0] if remaining else None}"


def test_candidates_empty_history():
    mem = new_memory()
    assert mem.get_compress_candidates() == []


def test_summaries_roundtrip():
    mem = new_memory()
    mem.append_summary("摘要一")
    mem.append_summary("摘要二")
    assert mem.get_summaries() == ["摘要一", "摘要二"], "摘要应按写入顺序返回"


def test_delete_messages_partial_syncs_cache():
    mem = new_memory()
    seed(mem, 6)  # 12 条
    cands = mem.get_compress_candidates()
    assert len(cands) == 10
    mem.delete_messages_by_ids([c["id"] for c in cands])
    assert len(mem.messages) == 2, f"缓存应与数据库同步: {len(mem.messages)}"
    assert mem.messages[0]["content"] == "问题5", "剩余应从第 6 轮开始"


def test_clear_history_clears_summaries():
    mem = new_memory()
    mem.append_summary("x")
    mem.clear_history()
    assert mem.get_summaries() == [], "clear_history 应清空摘要"


# ---------------------------------------------------------------------- #
# 集成测试：触发链路（>24 条 → 摘要 → 删除 → 注入 system prompt）             #
# ---------------------------------------------------------------------- #

async def test_full_compression_flow():
    ws = _tmp()
    try:
        client = CompressFakeClient()
        agent = make_agent(ws, client)
        for i in range(13):  # 26 条
            agent.memory.add_message({"role": "user", "content": f"早期问题{i}"})
            agent.memory.add_message({"role": "assistant", "content": f"早期回答{i}"})

        async for _ in agent.chat_stream("当前问题"):
            pass

        summaries = agent.memory.get_summaries()
        assert summaries, "超过阈值后应生成摘要"
        assert summaries[0] == "这是压缩后的早期对话摘要。"
        assert client.summary_calls == 1, "只应触发一次压缩"
        # 26(预置) + 2(本轮) - 10(压缩) = 18
        assert len(agent.memory.messages) == 18, f"压缩后应剩 18 条，实际 {len(agent.memory.messages)}"
        assert agent.memory.messages[0]["content"] == "早期问题5", "最早的 10 条应被删除"
        assert "# 早前对话摘要" in agent.context.build_system_prompt(), "摘要应注入 system prompt"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


async def test_failure_keeps_messages():
    ws = _tmp()
    try:
        client = CompressFakeClient(fail_summary=True)
        agent = make_agent(ws, client)
        for i in range(13):
            agent.memory.add_message({"role": "user", "content": f"早期问题{i}"})
            agent.memory.add_message({"role": "assistant", "content": f"早期回答{i}"})

        async for _ in agent.chat_stream("当前问题"):
            pass

        assert agent.memory.get_summaries() == [], "失败时不应写入摘要"
        assert len(agent.memory.messages) == 28, "失败时一条消息都不应删除"
    finally:
        shutil.rmtree(ws, ignore_errors=True)


async def test_below_threshold_no_compression():
    ws = _tmp()
    try:
        client = CompressFakeClient()
        agent = make_agent(ws, client)
        for i in range(4):  # 8 条，未超阈值
            agent.memory.add_message({"role": "user", "content": f"问题{i}"})
            agent.memory.add_message({"role": "assistant", "content": f"回答{i}"})

        async for _ in agent.chat_stream("当前问题"):
            pass

        assert client.summary_calls == 0, "未超阈值不应调用摘要模型"
        assert agent.memory.get_summaries() == []
    finally:
        shutil.rmtree(ws, ignore_errors=True)


# ---------------------------------------------------------------------- #
# 运行器                                                                    #
# ---------------------------------------------------------------------- #

SYNC_TESTS = [
    test_candidates_simple_rounds,
    test_candidates_tool_chain_included,
    test_candidates_incomplete_tool_round_rejected,
    test_candidates_ends_at_final_assistant_not_tool,
    test_candidates_empty_history,
    test_summaries_roundtrip,
    test_delete_messages_partial_syncs_cache,
    test_clear_history_clears_summaries,
]
ASYNC_TESTS = [
    test_full_compression_flow,
    test_failure_keeps_messages,
    test_below_threshold_no_compression,
]


async def main():
    print("=" * 50)
    print("上下文压缩功能测试")
    print("=" * 50)
    results = []

    shutil.rmtree(TMP_DIR, ignore_errors=True)  # 清理上次残留
    os.makedirs(TMP_DIR, exist_ok=True)

    for fn in SYNC_TESTS:
        try:
            fn()
            results.append((fn.__name__, True))
            print(f"  PASS {fn.__name__}")
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  FAIL {fn.__name__}: {type(e).__name__}: {e}")

    for fn in ASYNC_TESTS:
        try:
            await fn()
            results.append((fn.__name__, True))
            print(f"  PASS {fn.__name__}")
        except Exception as e:
            results.append((fn.__name__, False))
            print(f"  FAIL {fn.__name__}: {type(e).__name__}: {e}")

    failed = [name for name, ok in results if not ok]
    shutil.rmtree(TMP_DIR, ignore_errors=True)  # 清理本次残留
    print("=" * 50)
    print(f"总结: {len(results) - len(failed)}/{len(results)} 通过"
          + (f"，失败: {failed}" if failed else ""))
    print("=" * 50)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
