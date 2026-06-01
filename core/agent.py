import os
from typing import AsyncGenerator, Dict, Any, Callable

from openai import AsyncOpenAI

from .tools import ToolRegistry, ApprovalManager
from .skills import SkillsLoader
from .memory import MemoryStore
from .context import ContextBuilder
from .loop import AgentLoop
from .knowledge import KnowledgeBase

class TinyAgent:
    """
    高层封装：TinyAgent
    这是提供给外部调用的主要入口。内部组合了 Memory、Skills、Context 和 Loop 等组件。
    """
    def __init__(self, workspace_dir: str, openai_api_key: str = None, base_url: str = None, model: str = "gpt-4o-mini"):
        """
        初始化 Agent。
        :param workspace_dir: 工作区目录（用于存放 skills 和 memory）
        :param openai_api_key: OpenAI 兼容的 API Key。可使用环境变量 OPENAI_API_KEY 作为备用
        :param base_url: OpenAI 兼容接口的代理/服务地址。例如 Deepseek 的 endpoint
        :param model: 模型名
        """
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)
        
        # 初始化外部模型客户端
        api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
                raise ValueError("未提供 openai_api_key 或环境变量 OPENAI_API_KEY 中找不到 API Key。")
            
        api_kwargs = {"api_key": api_key}
        if base_url:
            api_kwargs["base_url"] = base_url
            
        self.client = AsyncOpenAI(**api_kwargs)
        
        # 初始化四大核心金刚
        self.memory = MemoryStore(workspace_dir)
        self.skills = SkillsLoader(workspace_dir)
        self.knowledge = KnowledgeBase(workspace_dir)
        self.tools = ToolRegistry(knowledge_base=self.knowledge)
        self.context = ContextBuilder(self.memory, self.skills, workspace_dir)
        # 人工审批管理器（Human-in-the-Loop）：高风险工具执行前请求用户确认
        self.approval_manager = ApprovalManager()
        self.loop = AgentLoop(self.client, self.tools, model=model,
                              approval_manager=self.approval_manager)

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
        async for event in self.loop.run(messages_payload):
            if event["type"] == "turn_end":
                # 解析本轮的所有辅助和回复消息并添加到 Memory 中
                new_msgs = event.get("new_messages", [])
                for idx, msg in enumerate(new_msgs):
                    # User 的不重复添加，其余添加进记忆（比如 assistant 和 tool）
                    self.memory.add_message(msg)
            elif event["type"] == "token_usage":
                # 保存 token 到持久化记忆
                p_tokens = event.get("prompt_tokens", 0)
                c_tokens = event.get("completion_tokens", 0)
                self.memory.add_tokens(p_tokens, c_tokens)
                yield event
            else:
                yield event
                
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
