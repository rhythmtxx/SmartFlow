#!/usr/bin/env python3
"""
SmartFlow 评估集运行器（Eval Harness）

用一组端到端任务量化 Agent 的行为质量，输出结构化报告。

两种模式：
  mock（默认，零成本）：用脚本化 FakeClient 让模型按计划返回 tool_call，
      验证 Agent 的工具调用链是否正确执行、结果是否正确回传。
      适合 CI / 开发期快速回归。
  real：使用真实 LLM 跑完整链路，按 checks 规则校验最终产物
      （输出文件存在/包含关键词、最终回复包含关键词），并统计 token 消耗。
      需要配置有效的 LLM API Key。

用法：
  python eval/run_eval.py                    # 跑全部 mock 任务
  python eval/run_eval.py --mode real        # 跑全部 real 任务（需 API Key）
  python eval/run_eval.py --mode all         # mock + real
  python eval/run_eval.py --task read_and_summarize
  python eval/run_eval.py --report eval/report.json
"""
import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

# 保证能从项目根 import core.*
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.tools import ToolRegistry, ApprovalManager
from core.loop import AgentLoop
from fakes import ScriptedClient

TASKS_DIR = Path(__file__).resolve().parent / "tasks"
TMP_DIR = Path(__file__).resolve().parent / "tmp"
DEFAULT_REPORT = Path(__file__).resolve().parent / "report.json"

# 占位符 Key 视为"未配置"
_PLACEHOLDER_KEYS = {"", "your-api-key-here", "your-api-key"}


# ---------------------------------------------------------------------- #
# 任务加载与环境准备                                                        #
# ---------------------------------------------------------------------- #

def load_tasks() -> list:
    tasks = []
    for f in sorted(TASKS_DIR.glob("*.json")):
        with open(f, encoding="utf-8") as fh:
            tasks.append(json.load(fh))
    return tasks


def make_workspace(task_name: str) -> Path:
    """每个任务使用独立临时工作区，互不污染。"""
    ws = TMP_DIR / task_name
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def setup_files(ws: Path, files: list):
    """按任务声明创建工作区文件（相对路径，如 outputs/sample.txt）。"""
    for spec in files or []:
        p = ws / spec["path"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(spec.get("content", ""), encoding="utf-8")


def load_api_key() -> str:
    """读取 LLM API Key：环境变量优先，其次 config.yaml。"""
    key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    if key:
        return key
    cfg_path = ROOT / "config.yaml"
    if cfg_path.exists():
        try:
            import yaml
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            key = (cfg.get("llm") or {}).get("api_key", "")
        except Exception:
            key = ""
    return key or ""


# ---------------------------------------------------------------------- #
# Mock 模式：脚本化验证工具调用链                                            #
# ---------------------------------------------------------------------- #

async def run_mock(task: dict, ws: Path) -> dict:
    plan = task["mock"]["tool_sequence"]
    final_reply = task["mock"].get("final_reply", "处理完毕。")
    client = ScriptedClient(plan, final_reply)
    registry = ToolRegistry()
    approval_mgr = ApprovalManager()
    loop = AgentLoop(client, registry, approval_manager=approval_mgr, approval_timeout=10)

    messages = [{"role": "user", "content": task["user_message"]}]
    executed: list = []
    errors: list = []

    async def runner():
        async for event in loop.run(messages):
            t = event["type"]
            if t == "approval_required":
                # 自动同意高风险工具（同时验证 HITL 审批链路本身可用）
                approval_mgr.resolve(event["approval_id"], True)
            elif t == "tool_call_start":
                executed.append(event["name"])
            elif t == "tool_call_end":
                summary = event["result_summary"]
                if "错误" in summary or "失败" in summary:
                    errors.append(f"{event['name']}: {summary}")

    await runner()

    expected = [step["tool"] for step in plan]
    failures = []
    if executed != expected:
        failures.append(f"工具序列不匹配: 期望 {expected}，实际 {executed}")
    if errors:
        failures.append("工具执行报错: " + " | ".join(errors))
    if client.call_count != len(plan) + 1:
        failures.append(f"轮数异常: 期望 {len(plan) + 1}，实际 {client.call_count}")

    return {
        "task": task["name"],
        "mode": "mock",
        "passed": not failures,
        "rounds": client.call_count,
        "tokens": {"prompt": 0, "completion": 0, "total": 0},
        "tool_sequence": executed,
        "failures": failures,
    }


# ---------------------------------------------------------------------- #
# Real 模式：真实 LLM + 产物校验                                            #
# ---------------------------------------------------------------------- #

def check_output_file(ws: Path, spec) -> list:
    """校验输出文件：存在 / 包含关键词。返回失败列表。"""
    failures = []
    path = spec if isinstance(spec, str) else spec["path"]
    p = ws / path
    if not p.exists():
        return [f"输出文件不存在: {path}"]
    if isinstance(spec, dict) and spec.get("keywords"):
        content = p.read_text(encoding="utf-8", errors="replace")
        for kw in spec["keywords"]:
            if kw not in content:
                failures.append(f"输出文件 {path} 缺少关键词: {kw!r}")
    return failures


async def run_real(task: dict, ws: Path) -> dict:
    from core.agent import TinyAgent
    from core.knowledge import KnowledgeBase

    api_key = load_api_key()
    if not api_key or api_key.strip() in _PLACEHOLDER_KEYS:
        return {
            "task": task["name"],
            "mode": "real",
            "skipped": True,
            "passed": False,
            "failures": ["未配置有效 LLM API Key（LLM_API_KEY 或 config.yaml）"],
        }

    # 任务可声明 setup_knowledge：运行前把指定文件导入临时工作区的知识库（RAG 用）
    # KnowledgeBase 的 chroma client 是模块级懒加载单例，与 TinyAgent 内部实例共享同一 db_path
    for rel in task.get("setup_knowledge", []):
        result = KnowledgeBase(str(ws)).add_document(str(ws / rel))
        if not result.get("success"):
            return {
                "task": task["name"], "mode": "real", "passed": False,
                "failures": [f"知识库导入失败: {result.get('error')}"],
            }

    agent = TinyAgent(str(ws), openai_api_key=api_key, model=os.environ.get("LLM_MODEL", "deepseek-chat"))
    tokens = {"prompt": 0, "completion": 0, "total": 0}
    final_text = ""
    rounds = 0

    async for event in agent.chat_stream(task["user_message"]):
        t = event["type"]
        if t == "text_delta":
            final_text += event["content"]
        elif t == "token_usage":
            tokens["prompt"] += event.get("prompt_tokens", 0)
            tokens["completion"] += event.get("completion_tokens", 0)
            tokens["total"] += event.get("total_tokens", 0)
        elif t == "tool_call_start":
            rounds += 1
        elif t == "approval_required":
            # 真实模式也自动同意（避免评估挂起等待人工）
            agent.approval_manager.resolve(event["approval_id"], True)
        elif t == "error":
            return {
                "task": task["name"], "mode": "real", "passed": False,
                "rounds": rounds, "tokens": tokens, "failures": [f"LLM/工具错误: {event['content']}"],
            }

    failures = []
    checks = task.get("checks", {})
    for spec in checks.get("output_file_exists", []):
        failures += check_output_file(ws, spec)
    for spec in checks.get("output_file_contains", []):
        failures += check_output_file(ws, spec)
    for kw in checks.get("final_reply_contains", []):
        if kw not in final_text:
            failures.append(f"最终回复缺少关键词: {kw!r}")

    return {
        "task": task["name"], "mode": "real", "passed": not failures,
        "rounds": rounds, "tokens": tokens, "failures": failures,
    }


# ---------------------------------------------------------------------- #
# 执行与报告                                                               #
# ---------------------------------------------------------------------- #

async def run_task(task: dict) -> dict:
    ws = make_workspace(task["name"])
    setup_files(ws, task.get("setup_files", []))
    old_cwd = Path.cwd()
    os.chdir(ws)  # 让工具内的相对路径（outputs/xxx）落在临时工作区
    t0 = time.time()
    try:
        if task.get("mode") == "real":
            result = await run_real(task, ws)
        else:
            result = await run_mock(task, ws)
    finally:
        os.chdir(old_cwd)
    result["duration_ms"] = int((time.time() - t0) * 1000)
    return result


def print_report(results: list):
    print("\n" + "=" * 78)
    print(" SmartFlow Eval Report")
    print("=" * 78)
    print(f" {'Task':<24} {'Mode':<6} {'Status':<8} {'Rounds':<7} {'Tokens':<8} Detail")
    print("-" * 78)
    for r in results:
        status = "SKIP" if r.get("skipped") else ("PASS" if r["passed"] else "FAIL")
        detail = ", ".join(r.get("failures", []))
        if not detail and r.get("tool_sequence"):
            detail = f"tools={r['tool_sequence']}"
        tok = r.get("tokens", {}).get("total", 0)
        rounds = r.get("rounds", "-")
        print(f" {r['task']:<24} {r['mode']:<6} {status:<8} {str(rounds):<7} {str(tok):<8} {detail[:50]}")
    print("-" * 78)

    total = len(results)
    ran = [r for r in results if not r.get("skipped")]
    passed = sum(1 for r in ran if r["passed"])
    if ran:
        avg_rounds = sum(r.get("rounds", 0) for r in ran) / len(ran)
        avg_tokens = sum(r.get("tokens", {}).get("total", 0) for r in ran) / len(ran)
        print(f" Summary: {passed}/{len(ran)} passed ({passed / len(ran) * 100:.1f}%)  "
              f"avg_rounds={avg_rounds:.1f}  avg_tokens={avg_tokens:.0f}  "
              f"skipped={total - len(ran)}")
    print("=" * 78)


def main():
    parser = argparse.ArgumentParser(description="SmartFlow Eval Harness")
    parser.add_argument("--mode", choices=["mock", "real", "all"], default="mock",
                        help="运行模式（默认 mock，零成本）")
    parser.add_argument("--task", help="只运行指定任务（按 name 过滤）")
    parser.add_argument("--report", default=str(DEFAULT_REPORT), help="报告输出路径")
    args = parser.parse_args()

    tasks = load_tasks()
    if args.task:
        tasks = [t for t in tasks if t["name"] == args.task]
    if args.mode == "mock":
        tasks = [t for t in tasks if t.get("mode") != "real"]
    elif args.mode == "real":
        tasks = [t for t in tasks if t.get("mode") == "real"]
    # mode == all：全部

    if not tasks:
        print("没有匹配的任务。")
        sys.exit(1)

    print(f"Running {len(tasks)} task(s) in [{args.mode}] mode ...")
    results = asyncio.run(_run_all(tasks))

    print_report(results)

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": args.mode,
        "total": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "results": results,
    }
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告已保存: {out}")

    # 退出码：有失败/跳过非全过则返回 1（便于 CI 判断）
    ran = [r for r in results if not r.get("skipped")]
    sys.exit(0 if ran and all(r["passed"] for r in ran) else 1)


async def _run_all(tasks):
    results = []
    for task in tasks:
        try:
            results.append(await run_task(task))
        except Exception as e:
            results.append({
                "task": task.get("name", "unknown"),
                "mode": task.get("mode", "mock"),
                "passed": False,
                "failures": [f"运行异常: {e}"],
            })
    return results


if __name__ == "__main__":
    main()
