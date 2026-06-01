import os
import json
import asyncio
import re
import uuid
from typing import Dict, Any, Callable, List

class BaseTool:
    """
    基础工具类，所有自定义工具都需要继承此类。
    提供了工具的名称、描述、参数结构等大模型需要的元数据。

    risk_level 风险分级（用于 Human-in-the-Loop 人工审批）：
      - "low":    只读、无副作用（如 read_file）。直接执行。
      - "medium": 写入但通常可恢复（如 write_file、edit_file）。直接执行。
      - "high":   不可逆或影响系统（如 exec 执行 Shell 命令）。执行前需用户审批。
    """
    def __init__(self, name: str, description: str, parameters: Dict[str, Any], risk_level: str = "low"):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.risk_level = risk_level

    def to_openai_function(self) -> Dict[str, Any]:
        """将工具转换为 OpenAI API 兼容的 function 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

    async def execute(self, **kwargs) -> str:
        """执行工具的具体逻辑，子类必须实现"""
        raise NotImplementedError("子类必须实现 execute 方法")


class ReadFileTool(BaseTool):
    """读取文件工具"""
    def __init__(self):
        super().__init__(
            name="read_file",
            description="读取指定文件的内容。注意，如果文件太大可能会截断或报错。",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件的绝对或相对路径"
                    }
                },
                "required": ["path"]
            }
        )

    async def execute(self, path: str) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                # 防止单次读取文件过大，限制前10000个字符
                if len(content) > 10000:
                    return content[:10000] + "\n...[文件内容过长被截断]"
                return content
        except Exception as e:
            return f"读取文件失败: {str(e)}"


class WriteFileTool(BaseTool):
    """写入文件工具"""
    def __init__(self):
        super().__init__(
            name="write_file",
            description="将内容写入到指定文件中。如果文件不存在则会创建，如果存在则会覆盖。",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要写入的文件的绝对或相对路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要写入的内容文本"
                    }
                },
                "required": ["path", "content"]
            },
            risk_level="medium"  # 写入文件，通常可恢复
        )

    async def execute(self, path: str, content: str) -> str:
        try:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"成功写入文件: {path}"
        except Exception as e:
            return f"写入文件失败: {str(e)}"


class EditFileTool(BaseTool):
    """编辑文件工具 (简单查找替换)"""
    def __init__(self):
        super().__init__(
            name="edit_file",
            description="编辑指定文件的内容。通过查找旧字符串并替换为新字符串。建议先读取文件内容确认。",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要编辑的文件的绝对或相对路径"
                    },
                    "old_str": {
                        "type": "string",
                        "description": "要被替换的原始文本字符串"
                    },
                    "new_str": {
                        "type": "string",
                        "description": "替换后的新文本字符串"
                    }
                },
                "required": ["path", "old_str", "new_str"]
            },
            risk_level="medium"  # 编辑文件，通常可恢复
        )

    async def execute(self, path: str, old_str: str, new_str: str) -> str:
        try:
            if not os.path.exists(path):
                return f"错误：文件 {path} 不存在"
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old_str not in content:
                return f"错误：在文件内容中未找到指定的 old_str"
            
            new_content = content.replace(old_str, new_str)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            return f"成功编辑文件: {path}"
        except Exception as e:
            return f"编辑文件失败: {str(e)}"


class ShellTool(BaseTool):
    """
    执行 Shell 命令工具。
    提供执行系统命令的能力，配有超时与高危命令拦截以维护安全。
    """
    def __init__(self, timeout: int = 60):
        super().__init__(
            name="exec",
            description="执行 Shell 命令并返回输出。谨慎使用。",
            parameters={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 Shell 命令"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "可选的执行目录"
                    }
                },
                "required": ["command"]
            },
            risk_level="high"  # Shell 命令不可逆，执行前需人工审批
        )
        self.timeout = timeout
        # 拦截常见高危操作
        self.deny_patterns = [
            r"\brm\s+-[rf]{1,2}\b",          # rm -r, rm -rf, rm -fr
            r"\bdel\s+/[fq]\b",              # del /f, del /q
            r"\brmdir\s+/s\b",               # rmdir /s
            r"(?:^|[;&|]\s*)format\b",       # format
            r"\b(mkfs|diskpart)\b",          # disk operations
            r"\bdd\s+if=",                   # dd
            r">\s*/dev/sd",                  # write to disk
            r"\b(shutdown|reboot|poweroff)\b",  # system power
            r":\(\)\s*\{.*\};\s*:",          # fork bomb
        ]

    async def execute(self, command: str, working_dir: str = None) -> str:
        cwd = working_dir or os.getcwd()
        guard_error = self._guard_command(command)
        if guard_error:
            return guard_error

        try:
            # Windows 上 asyncio 子进程需要 ProactorEventLoop，
            # 用 subprocess + asyncio.to_thread 绕过兼容性问题
            import subprocess
            import asyncio as _asyncio

            def _run():
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    cwd=cwd,
                    timeout=self.timeout,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                parts = []
                if result.stdout:
                    parts.append(result.stdout)
                if result.stderr and result.stderr.strip():
                    parts.append(f"STDERR:\n{result.stderr}")
                if result.returncode != 0:
                    parts.append(f"\n退出状态码: {result.returncode}")
                return "\n".join(parts) if parts else "(无输出)"

            result = await _asyncio.to_thread(_run)

            if len(result) > 10000:
                result = result[:10000] + f"\n... (截断，剩余 {len(result) - 10000} 个字符)"

            return result

        except subprocess.TimeoutExpired:
            return f"错误：命令执行超时（超过 {self.timeout} 秒）"
        except Exception as e:
            return f"执行命令时发生异常: {str(e)}"

    def _guard_command(self, command: str) -> str | None:
        cmd = command.strip()
        lower = cmd.lower()
        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return "错误: 命令被安全策略拦截 (检测到危险模式)"
        return None


class SearchKnowledgeTool(BaseTool):
    """
    知识库检索工具（RAG）。
    在已导入的本地文档中检索与问题最相关的内容片段，
    帮助 Agent 回答私域知识问题，减少幻觉。
    """
    def __init__(self, knowledge_base):
        super().__init__(
            name="search_knowledge",
            description=(
                "在本地知识库中检索与问题相关的内容。"
                "当用户询问已上传文档中的内容时使用此工具。"
                "返回最相关的文本片段及其来源文件。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "要检索的问题或关键词"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回最相关的片段数量，默认 3",
                        "default": 3
                    }
                },
                "required": ["query"]
            },
            risk_level="low"  # 只读检索，无副作用
        )
        self.kb = knowledge_base

    async def execute(self, query: str, top_k: int = 3) -> str:
        import asyncio
        # 向量检索是 CPU 密集型操作，用 to_thread 避免阻塞事件循环
        results = await asyncio.to_thread(self.kb.search, query, top_k)

        if not results:
            return "知识库为空或未找到相关内容。请先上传相关文档。"

        # 格式化输出，让大模型容易理解
        parts = [f"检索到 {len(results)} 条相关内容：\n"]
        for i, r in enumerate(results, 1):
            parts.append(
                f"【片段 {i}】来源：{r['source']}（相似度：{r['score']:.2f}）\n{r['text']}"
            )
        return "\n\n".join(parts)


class ToolRegistry:
    """工具注册中心，负责管理和执行所有工具"""
    def __init__(self, knowledge_base=None):
        self.tools: Dict[str, BaseTool] = {}
        # 默认注册基础的文件操作工具
        self.register(ReadFileTool())
        self.register(WriteFileTool())
        self.register(EditFileTool())
        # 注册 Shell 工具
        self.register(ShellTool())
        # 注册 RAG 知识库检索工具（需要传入 KnowledgeBase 实例）
        if knowledge_base is not None:
            self.register(SearchKnowledgeTool(knowledge_base))

    def register(self, tool: BaseTool):
        """注册一个新工具"""
        self.tools[tool.name] = tool

    def get_definitions(self) -> List[Dict[str, Any]]:
        """获取所有已注册工具的 OpenAI function 定义列表"""
        return [tool.to_openai_function() for tool in self.tools.values()]

    def get_risk_level(self, name: str) -> str:
        """查询某个工具的风险等级。工具不存在时返回 'low'（不拦截未知工具的判断交给 execute）。"""
        tool = self.tools.get(name)
        return tool.risk_level if tool else "low"

    async def execute(self, name: str, arguments_json: str) -> str:
        """
        根据工具名称和 JSON 格式的参数执行对应的工具
        """
        if name not in self.tools:
            return f"错误：未找到名为 '{name}' 的工具"
        
        tool = self.tools[name]
        try:
            kwargs = json.loads(arguments_json)
            result = await tool.execute(**kwargs)
            return str(result)
        except json.JSONDecodeError:
            return "错误：提供的参数不是有效的 JSON 格式"
        except Exception as e:
            return f"执行工具 '{name}' 时发生异常: {str(e)}"


class ApprovalManager:
    """
    人工审批管理器 (Human-in-the-Loop)。

    职责：在 Agent 想执行高风险工具时，充当“等待方”(loop.py) 和
    “响应方”(app.py 的 /api/approve 接口) 之间的桥梁。

    工作原理：
      1. loop.py 调用 create_request() 登记一个待审批请求，拿到 approval_id
      2. loop.py 调用 wait_for_approval() 挂起等待（底层用 asyncio.Event）
      3. 用户在前端点击同意/拒绝，app.py 收到后调用 resolve() 写入结果并唤醒
      4. loop.py 被唤醒，拿到 True/False 决定是否执行工具

    为什么需要这个类？因为 loop.py 和 app.py 是两个独立的协程，
    无法直接共享变量，必须通过这个共享的字典(self.pending)间接通信。
    """
    def __init__(self):
        # approval_id -> {"event": asyncio.Event, "result": bool | None}
        self.pending: Dict[str, Dict[str, Any]] = {}

    def create_request(self) -> str:
        """登记一个新的审批请求，返回唯一 approval_id。"""
        approval_id = str(uuid.uuid4())
        self.pending[approval_id] = {
            "event": asyncio.Event(),  # 异步“开关”，初始为关闭(未 set)
            "result": None
        }
        return approval_id

    async def wait_for_approval(self, approval_id: str, timeout: int = 60) -> bool:
        """
        挂起当前协程，等待用户响应。带超时保护。
        返回 True(同意) / False(拒绝或超时)。
        """
        record = self.pending.get(approval_id)
        if record is None:
            return False  # 请求不存在，安全起见拒绝

        try:
            # 在这里挂起，直到 event 被 set 或超时
            await asyncio.wait_for(record["event"].wait(), timeout=timeout)
            return bool(record["result"])
        except asyncio.TimeoutError:
            return False  # 超时默认拒绝（安全默认值）
        finally:
            # 无论成功/超时都清理，避免内存泄漏
            self.pending.pop(approval_id, None)

    def resolve(self, approval_id: str, approved: bool) -> bool:
        """
        收到用户的审批结果，写入并唤醒等待方。
        返回是否成功（False 表示该请求不存在或已超时清理）。
        """
        record = self.pending.get(approval_id)
        if record is None:
            return False
        record["result"] = approved
        record["event"].set()  # 打开开关 -> 唤醒 wait_for_approval
        return True
