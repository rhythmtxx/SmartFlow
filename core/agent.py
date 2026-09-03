import logging
import os
from typing import AsyncGenerator, Dict, Any, Optional

from openai import AsyncOpenAI

from .tools import ToolRegistry, ApprovalManager
from .skills import SkillsLoader
from .memory import MemoryStore
from .context import ContextBuilder
from .loop import AgentLoop
from .knowledge import KnowledgeBase

logger = logging.getLogger(__name__)

# 上下文压缩默认参数（config.yaml 的 agent.* 可覆盖）
SUMMARY_MAX_CHARS = 300
SUMMARY_ITEM_TRUNCATE = 200  # 摘要输入里单条 tool 结果截断长度


class TinyAgent:
    """
    高层封装：TinyAgent
    这是提供给外部调用的主要入口。内部组合了 Memory、Skills、Context 和 Loop 等组件。

    多会话设计：
    - 无状态组件（LLM client / skills / knowledge / tools）通过 `build_shared()` 构建一次，
      由 SessionManager 全局共享，避免每个会话重复加载。
    - 有状态组件（MemoryStore / ApprovalManager）按 `session_id` 隔离。
    """
    def __init__(self, workspace_dir: str, session_id: str = "default",
                 shared: Optional[Dict[str, Any]] = None,
                 openai_api_key: str = None, base_url: str = None,
                 model: str = "gpt-4o-mini",
                 agent_config: Optional[Dict[str, Any]] = None):
        """
        初始化 Agent。
        :param workspace_dir: 工作区目录（用于存放 skills 和 memory）
        :param session_id: 会话 ID，用于隔离对话记忆与审批状态
        :param shared: 共享组件字典（由 SessionManager 传入）；不传则自行构建
        :param openai_api_key: OpenAI 兼容的 API Key。可使用环境变量 OPENAI_API_KEY 作为备用
        :param base_url: OpenAI 兼容接口的代理/服务地址。例如 Deepseek 的 endpoint
        :param model: 模型名
        :param agent_config: Agent 运行参数（max_iterations/window_size/compress_threshold/approval_timeout）
        """
        self.workspace_dir = workspace_dir
        self.session_id = session_id
        os.makedirs(workspace_dir, exist_ok=True)

        cfg = agent_config or {}
        # 上下文压缩触发阈值：活跃消息数超过该值触发压缩（config 可覆盖）
        self.compress_threshold = cfg.get("compress_threshold", 24)

        # 共享组件：外部传入则复用（多会话共享），否则自行构建（兼容单会话用法）
        if shared is None:
            shared = TinyAgent.build_shared(workspace_dir, openai_api_key, base_url, model)
        self.shared = shared

        self.client = shared["client"]
        self.skills = shared["skills"]
        self.knowledge = shared["knowledge"]
        self.tools = shared["tools"]

        # 会话隔离状态
        self.memory = MemoryStore(workspace_dir, session_id=session_id)
        self.context = ContextBuilder(self.memory, self.skills, workspace_dir,
                                      window_size=cfg.get("window_size", 20))
        # 人工审批管理器（Human-in-the-Loop）：高风险工具执行前请求用户确认
        # 每个会话独立，避免跨会话互相 resolve
        self.approval_manager = ApprovalManager()
        self.loop = AgentLoop(self.client, self.tools, model=model,
                              approval_manager=self.approval_manager,
                              approval_timeout=cfg.get("approval_timeout", 60),
                              max_iterations=cfg.get("max_iterations", 10))
        # 上下文压缩防重入标志（HTTP 层已有会话锁，这里是直接调用方的第二道防线）
        self._compressing = False

    @staticmethod
    def build_shared(workspace_dir: str, openai_api_key: str = None,
                     base_url: str = None, model: str = "gpt-4o-mini",
                     tool_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构建全局共享的组件（只构建一次，多个会话复用）：
        - LLM 客户端（无状态）
        - 技能加载器（只读）
        - 知识库（只读，embedding 模型本身是模块级懒加载单例）
        - 工具注册中心（只读）
        :param tool_config: config.yaml 的 tools 段（web_search.api_key / code_exec.*），默认 None
        """
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未提供 openai_api_key 或环境变量 OPENAI_API_KEY 中找不到 API Key。")

        api_kwargs = {"api_key": api_key}
        if base_url:
            api_kwargs["base_url"] = base_url

        client = AsyncOpenAI(**api_kwargs)
        skills = SkillsLoader(workspace_dir)
        knowledge = KnowledgeBase(workspace_dir)
        tools = ToolRegistry(knowledge_base=knowledge, tool_config=tool_config, workspace_dir=workspace_dir)

        return {
            "client": client,
            "skills": skills,
            "knowledge": knowledge,
            "tools": tools,
        }

    async def chat_stream(self, user_message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        核心的对外交互接口。接收字符串，返回事件流（AsyncGenerator）。
        
        调用流程概览：
        1. 拿到用户的当前问题。
        2. 将问题连同历史记录、系统提示组装成一整条消息 Payload：`messages`。
        3. 用 Generator 的方式透传 `loop` 执行产生的所有状态与文字输出。
        4. 最后完成时，将本次对答新增好的多轮记录（User, Assistant, Tool等）追加进入记忆存储库 `MemoryStore`。
        """
        # 1. 组装发往大模型的初始 Payload
        messages_payload = self.context.build_messages(user_message)
        
        # 把用户的消息率先单独加入记忆，代表一轮交互正式开始
        self.memory.add_message({
            "role": "user",
            "content": user_message
        })
        
        # 2. 下沉进核心 Loop 返回流
        # 记录可观测性数据：tool_call 明细（start 缓存参数 → end 落库）与每轮 token
        tool_call_buffer: Dict[str, Dict[str, Any]] = {}
        async for event in self.loop.run(messages_payload):
            etype = event["type"]
            if etype == "turn_end":
                # 解析本轮的所有辅助和回复消息并添加到 Memory 中
                new_msgs = event.get("new_messages", [])
                for idx, msg in enumerate(new_msgs):
                    # User 的不重复添加，其余添加进记忆（比如 assistant 和 tool）
                    self.memory.add_message(msg)
                # 本轮完整落库后，尝试压缩最早的完整轮次（超阈值时）
                await self._maybe_compress()
            elif etype == "token_usage":
                # 保存 token 到持久化记忆 + 记录本轮明细（可观测性）
                p_tokens = event.get("prompt_tokens", 0)
                c_tokens = event.get("completion_tokens", 0)
                t_tokens = event.get("total_tokens", p_tokens + c_tokens)
                self.memory.add_tokens(p_tokens, c_tokens)
                self.memory.add_round(p_tokens, c_tokens, t_tokens)
                yield event
            elif etype == "tool_call_start":
                # 缓存参数，等 tool_call_end 时合成一条完整记录
                tool_call_buffer[event.get("id", "")] = event
                yield event
            elif etype == "tool_call_end":
                start = tool_call_buffer.pop(event.get("id", ""), {})
                self.memory.add_tool_call(
                    tool_name=event.get("name") or start.get("name", ""),
                    arguments=start.get("arguments", ""),
                    result_summary=event.get("result_summary", ""),
                )
                yield event
            else:
                yield event

    async def _maybe_compress(self):
        """
        上下文压缩：活跃消息超过阈值时，把最早一批完整轮次交给 LLM 压缩成
        ≤300 字摘要，先写入 summaries 表、成功后再删除原文。

        失败兜底：任何异常都静默跳过（不删任何消息、不阻塞对话）。
        """
        if self._compressing:
            return
        self._compressing = True
        try:
            if len(self.memory.messages) <= self.compress_threshold:
                return
            candidates = self.memory.get_compress_candidates()
            if not candidates:
                return
            history_text = "\n".join(
                f"{m.get('role')}: {str(m.get('content') or '')[:SUMMARY_ITEM_TRUNCATE]}"
                for m in candidates
            )
            prompt = (
                f"请将以下对话历史压缩成不超过 {SUMMARY_MAX_CHARS} 字的摘要。必须保留：\n"
                "1. 用户的偏好与关键要求\n"
                "2. 已完成的重要操作与结果\n"
                "3. 未完成或待办的事项\n"
                "忽略寒暄与无关细节。直接输出摘要，不要其他内容。\n\n"
                "--- 对话历史 ---\n"
                + history_text
            )
            resp = await self.client.chat.completions.create(
                model=self.loop.model,
                messages=[{"role": "user", "content": prompt}]
            )
            summary = (resp.choices[0].message.content or "").strip()
            if not summary:
                return
            self.memory.append_summary(summary[:SUMMARY_MAX_CHARS])
            self.memory.delete_messages_by_ids([m["id"] for m in candidates])
            logger.info(f"上下文压缩完成：删除 {len(candidates)} 条历史，摘要已入库")
        except Exception as e:
            logger.warning(f"上下文压缩失败，已跳过（不删除消息）: {e}")
        finally:
            self._compressing = False

    def get_skills_summary(self) -> list:
        """透出所有的技能清单用于前端呈现"""
        return self.skills.get_skills_summary()
        
    def get_tools_summary(self) -> list:
        """透出当前支持的工具清单"""
        return [{"name": t.name, "description": t.description} for t in self.tools.tools.values()]
    
    def clear_memory(self):
        """重置当前会话"""
        self.memory.clear_history()

    def resolve_approval(self, approval_id: str, approved: bool) -> bool:
        """
        提交一个高风险工具的审批结果（由 HTTP 接口 /api/approve 调用）。
        返回 True 表示成功唤醒等待中的工具调用；False 表示该请求不存在或已超时。
        """
        return self.approval_manager.resolve(approval_id, approved)
