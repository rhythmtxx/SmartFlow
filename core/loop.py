import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from openai import AsyncOpenAI

from .tools import ToolRegistry, ApprovalManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentLoop:
    """
    事件循环模块。
    核心职责：
    1. 调用模型获取流式返回
    2. 判断是返回纯文本还是触发 Tool Call
    3. 解析 Tool Call 并调度 `ToolRegistry` 执行
    4. 将工具的运行结果再反向注入上下文请求大模型（循环直到结束）
    5. 通过 Async Generator 把整个过程的状态透传给外部（用于 SSE 推送和可视化）
    6. 对高风险工具（risk_level=high）执行前触发人工审批（Human-in-the-Loop）
    """
    def __init__(self, client: AsyncOpenAI, tool_registry: ToolRegistry, model: str = "gpt-4o-mini",
                 approval_manager: Optional[ApprovalManager] = None, approval_timeout: int = 60):
        self.client = client
        self.tool_registry = tool_registry
        self.model = model
        # 审批管理器：为空则不启用人工审批（向后兼容）
        self.approval_manager = approval_manager
        self.approval_timeout = approval_timeout

    async def run(self, messages: list[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        启动与大模型的交互。
        产生字典形式的事件：
        {
          "type": "text_delta" | "tool_call_start" | "tool_call_end" | "token_usage",
          "content": "", ...
        }
        """
        current_messages = list(messages)
        max_iterations = 10  # 防止无限死循环调用工具的防御阈值
        iteration = 0
        tools_def = self.tool_registry.get_definitions()

        while iteration < max_iterations:
            iteration += 1
            
            # 清理消息历史中的非法字段（如空 tool_calls），兼容各路 API 后端
            cleaned_messages = []
            for m in current_messages:
                new_m = m.copy()
                # 某些后端不允许空的 tool_calls，直接剔除该 key
                if "tool_calls" in new_m and not new_m["tool_calls"]:
                    del new_m["tool_calls"]
                # 某些后端对 content=None 或 content="" 有不同偏好
                # 如果有 tool_calls，content 可以为 None。如果没 tool_calls，content 必须有值或省略。
                if "content" in new_m and new_m["content"] == "":
                    new_m["content"] = None
                cleaned_messages.append(new_m)

            api_kwargs = {
                "model": self.model,
                "messages": cleaned_messages,
                "stream": True,
                "stream_options": {"include_usage": True}
            }
            if tools_def:
                api_kwargs["tools"] = tools_def

            logger.info(f"[AgentLoop] 发起第 {iteration} 轮请求，携带 {len(cleaned_messages)} 条历史")
            
            try:
                response_stream = await self.client.chat.completions.create(**api_kwargs)
            except Exception as e:
                yield {"type": "error", "content": f"调用大模型API失败: {str(e)}"}
                break

            assistant_msg = {"role": "assistant", "content": ""}
            tool_call_buffer = {} # 用于在流式解析时重组 tool call 数据

            # 遍历流式数据块
            async for chunk in response_stream:
                # 记录 Token 消耗
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield {
                        "type": "token_usage",
                        "prompt_tokens": chunk.usage.prompt_tokens,
                        "completion_tokens": chunk.usage.completion_tokens,
                        "total_tokens": chunk.usage.total_tokens
                    }

                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                
                # 情况 1: 普通文本的 delta 输出
                if delta.content:
                    assistant_msg["content"] += delta.content
                    yield {"type": "text_delta", "content": delta.content}

                # 情况 2: 工具调用 (Tool Call) 的 stream 解析
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_call_buffer:
                            tool_call_buffer[idx] = {
                                "id": tc.id or "",
                                "type": "function",
                                "function": {
                                    "name": tc.function.name if tc.function and tc.function.name else "",
                                    "arguments": tc.function.arguments if tc.function and tc.function.arguments else ""
                                }
                            }
                        else:
                            if tc.id:
                                tool_call_buffer[idx]["id"] += tc.id
                            if tc.function:
                                if tc.function.name:
                                    tool_call_buffer[idx]["function"]["name"] += tc.function.name
                                if tc.function.arguments:
                                    tool_call_buffer[idx]["function"]["arguments"] += tc.function.arguments

            # 情况 1: 装配好了 tool_calls
            if tool_call_buffer:
                assistant_msg["tool_calls"] = [v for k, v in sorted(tool_call_buffer.items())]
            
            # 情况 2: 处理空内容，防止 OpenAI 报错
            if not assistant_msg["content"]:
                # 如果有工具调用，内容可以为 None；如果没有，某些后端可能要求省略或有内容
                assistant_msg["content"] = None

            current_messages.append(assistant_msg)

            # 判断是否有 tool call，没有就可以结束了
            if not assistant_msg.get("tool_calls"):
                break

            # 处理每个工具的调用结果
            for tc in assistant_msg["tool_calls"]:
                tool_name = tc["function"]["name"]
                tool_args_str = tc["function"]["arguments"]

                # 对前端发出执行工具开始的通知
                yield {
                    "type": "tool_call_start",
                    "id": tc["id"],
                    "name": tool_name,
                    "arguments": tool_args_str
                }

                # === Human-in-the-Loop 人工审批 ===
                # 若启用了审批管理器，且该工具为高风险，则执行前请求用户确认
                risk_level = self.tool_registry.get_risk_level(tool_name)
                if self.approval_manager is not None and risk_level == "high":
                    approval_id = self.approval_manager.create_request()

                    # 通知前端弹出审批窗口
                    yield {
                        "type": "approval_required",
                        "approval_id": approval_id,
                        "id": tc["id"],
                        "name": tool_name,
                        "arguments": tool_args_str,
                        "risk_level": risk_level,
                        "reason": f"工具 '{tool_name}' 属于高风险操作，执行前需要你的确认。"
                    }

                    logger.info(f"工具 '{tool_name}' 触发人工审批，等待用户响应 (id={approval_id})")

                    # 挂起等待用户响应（带超时，超时默认拒绝）
                    approved = await self.approval_manager.wait_for_approval(
                        approval_id, timeout=self.approval_timeout
                    )

                    # 告知前端审批结果（用于关闭弹窗、更新 UI）
                    yield {
                        "type": "approval_resolved",
                        "approval_id": approval_id,
                        "id": tc["id"],
                        "name": tool_name,
                        "approved": approved
                    }

                    if not approved:
                        # 用户拒绝或超时：不执行工具，把“被拒绝”作为工具结果回传给模型
                        reject_msg = f"用户拒绝了工具 '{tool_name}' 的执行请求（或确认超时）。操作已取消。"
                        logger.info(reject_msg)
                        yield {
                            "type": "tool_call_end",
                            "id": tc["id"],
                            "name": tool_name,
                            "result_summary": reject_msg
                        }
                        current_messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "name": tool_name,
                            "content": reject_msg
                        })
                        continue  # 跳过执行，处理下一个工具调用

                logger.info(f"执行工具 '{tool_name}' 参数: {tool_args_str}")

                # 实际执行
                result = await self.tool_registry.execute(tool_name, tool_args_str)
                logger.info(f"执行结果: {result[:100]}...")

                # 通知前端执行完毕并携带状态
                yield {
                    "type": "tool_call_end",
                    "id": tc["id"],
                    "name": tool_name,
                    "result_summary": result[:100] + ("..." if len(result) > 100 else "")
                }

                # 把结果注入 messages
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "name": tool_name,
                    "content": result
                })
        
        # 将 current_messages 这个回合内实际发生过的完整的增量历史提交回去保存
        # 具体来说是把 从 messages 传入进来的旧数据剥离，得到新产生的数据，交给外部。
        yield {
            "type": "turn_end",
            "new_messages": current_messages[len(messages):]
        }
