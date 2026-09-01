import json
import os
import sqlite3
from typing import List, Dict, Any


class MemoryStore:
    """
    记忆存储模块，基于 SQLite 持久化对话历史。

    相比原来的 JSON 文件存储，SQLite 的优势：
      1. 并发安全 — SQLite 内置文件级锁，多用户写入不会丢数据
      2. 按 session_id 隔离 — 多用户天然隔离，不需要多个文件
      3. 查询效率 — 取最近 N 条记录直接用 SQL LIMIT，不需要加载全部数据

    表结构：
      messages(id, session_id, role, content, created_at)
      tokens(session_id, prompt_tokens, completion_tokens)
      tool_calls(id, session_id, tool_name, arguments, result_summary, created_at)
      rounds(id, session_id, prompt_tokens, completion_tokens, total_tokens, created_at)
      summaries(id, session_id, content, created_at)  — 上下文压缩产物

    长期记忆（MEMORY.md）继续用文件存储，因为它是给 Agent 读写的 Markdown 文档。
    """

    def __init__(self, workspace_dir: str, session_id: str = "default"):
        self.memory_dir = os.path.join(workspace_dir, "memory")
        os.makedirs(self.memory_dir, exist_ok=True)

        self.session_id = session_id
        self.db_path = os.path.join(self.memory_dir, "memory.db")
        self.long_term_file = os.path.join(self.memory_dir, "MEMORY.md")

        self._init_db()

        # 内存缓存，避免每次 get_messages 都查数据库
        self.messages: List[Dict[str, Any]] = self._load_history()
        self.tokens: Dict[str, int] = self._load_tokens()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接（每次调用创建新连接，线程安全）"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表结构（如果不存在则创建）"""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS messages (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id  TEXT    NOT NULL,
                    content     TEXT    NOT NULL,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tokens (
                    session_id        TEXT PRIMARY KEY,
                    prompt_tokens     INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_messages_session
                    ON messages(session_id, id);

                -- 可观测性：工具调用记录
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id     TEXT    NOT NULL,
                    tool_name      TEXT    NOT NULL,
                    arguments      TEXT    DEFAULT '',
                    result_summary TEXT    DEFAULT '',
                    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_tool_calls_session
                    ON tool_calls(session_id, id);

                -- 可观测性：每轮 LLM 调用明细（token 消耗）
                CREATE TABLE IF NOT EXISTS rounds (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id        TEXT    NOT NULL,
                    prompt_tokens     INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens      INTEGER DEFAULT 0,
                    created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_rounds_session
                    ON rounds(session_id, id);

                -- 上下文压缩：早期对话摘要（先存摘要，成功后删原文）
                CREATE TABLE IF NOT EXISTS summaries (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT    NOT NULL,
                    content    TEXT    NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_summaries_session
                    ON summaries(session_id, id);
            """)

    def _load_history(self) -> List[Dict[str, Any]]:
        """从数据库加载当前 session 的全部对话记录"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT content FROM messages WHERE session_id = ? ORDER BY id",
                (self.session_id,)
            ).fetchall()
        result = []
        for row in rows:
            try:
                result.append(json.loads(row["content"]))
            except Exception:
                pass
        return result

    def _save_message_to_db(self, message: Dict[str, Any]):
        """把单条消息写入数据库"""
        content = json.dumps(message, ensure_ascii=False)
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO messages (session_id, content) VALUES (?, ?)",
                (self.session_id, content)
            )

    def _load_tokens(self) -> Dict[str, int]:
        """从数据库加载 token 统计"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT prompt_tokens, completion_tokens FROM tokens WHERE session_id = ?",
                (self.session_id,)
            ).fetchone()
        if row:
            return {"prompt": row["prompt_tokens"], "completion": row["completion_tokens"]}
        return {"prompt": 0, "completion": 0}

    def _save_tokens_to_db(self):
        """用 UPSERT 更新 token 统计（INSERT OR REPLACE）"""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO tokens (session_id, prompt_tokens, completion_tokens)
                   VALUES (?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                       prompt_tokens     = excluded.prompt_tokens,
                       completion_tokens = excluded.completion_tokens""",
                (self.session_id, self.tokens["prompt"], self.tokens["completion"])
            )

    # ------------------------------------------------------------------ #
    # 以下是对外接口，签名与原 JSON 版本完全一致，上层代码无需修改           #
    # ------------------------------------------------------------------ #

    def add_message(self, message: Dict[str, Any]):
        """新增一条消息到短期历史中并持久化"""
        self.messages.append(message)
        self._save_message_to_db(message)

    def get_messages(self, window_size: int = 20) -> List[Dict[str, Any]]:
        """
        获取对话历史（带安全截断）。
        截断必须从 user 消息开始，防止产生孤儿 tool_call 导致 API 报错。
        """
        if len(self.messages) <= window_size:
            return self.messages

        start_idx = max(0, len(self.messages) - window_size)
        while start_idx > 0 and self.messages[start_idx].get("role") != "user":
            start_idx -= 1

        return self.messages[start_idx:]

    # ------------------------------------------------------------------ #
    # 上下文压缩：摘要存取与候选选取                                          #
    # ------------------------------------------------------------------ #

    def get_summaries(self) -> List[str]:
        """按时间正序返回当前会话的全部早期对话摘要。"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT content FROM summaries WHERE session_id = ? ORDER BY id",
                (self.session_id,)
            ).fetchall()
        return [r["content"] for r in rows]

    def append_summary(self, content: str) -> None:
        """写入一条早期对话摘要。"""
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO summaries (session_id, content) VALUES (?, ?)",
                (self.session_id, content)
            )

    def get_compress_candidates(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        返回最早可压缩的完整轮次消息（带 id），空列表表示无候选。

        轮次规则：候选必须是完整轮次——从 user 开始，且**末尾必须是
        没有 tool_calls 的 assistant（final reply）**。只切在 final assistant
        处，保证删除后剩余历史以 user 开头，不会产生孤儿 tool 消息。
        一批里没有 final assistant（工具链未闭环）则返回空。
        """
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, content FROM messages WHERE session_id = ? ORDER BY id LIMIT ?",
                (self.session_id, max_messages)
            ).fetchall()
        msgs = []
        for r in rows:
            try:
                m = json.loads(r["content"])
            except Exception:
                continue  # 无法解析的消息不参与候选
            msgs.append({"id": r["id"], **m})

        # 防御：候选开头必须是 user（正常流程下最早消息总是 user）
        while msgs and msgs[0].get("role") != "user":
            msgs.pop(0)

        # 截止到最后一个 final assistant（无 tool_calls），保证轮次完整
        end = None
        for i, m in enumerate(msgs):
            if m.get("role") == "assistant" and not m.get("tool_calls"):
                end = i
        if end is None:
            return []
        return msgs[:end + 1]

    def delete_messages_by_ids(self, ids: List[int]) -> None:
        """删除指定 id 的消息，并重载内存缓存保持同步（删除是低频操作）。"""
        if not ids:
            return
        with self._get_conn() as conn:
            conn.executemany(
                "DELETE FROM messages WHERE session_id = ? AND id = ?",
                [(self.session_id, i) for i in ids]
            )
        self.messages = self._load_history()

    def add_tokens(self, prompt_tokens: int, completion_tokens: int):
        """累加 token 消耗"""
        self.tokens["prompt"] += prompt_tokens
        self.tokens["completion"] += completion_tokens
        self._save_tokens_to_db()

    def get_tokens(self) -> Dict[str, int]:
        """获取当前累加的 token 消耗"""
        return self.tokens

    # ------------------------------------------------------------------ #
    # 可观测性：工具调用与每轮 token 明细                                    #
    # ------------------------------------------------------------------ #

    def add_tool_call(self, tool_name: str, arguments: str = "", result_summary: str = "") -> None:
        """记录一次工具调用（名称、参数、结果摘要）。"""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO tool_calls (session_id, tool_name, arguments, result_summary)
                   VALUES (?, ?, ?, ?)""",
                (self.session_id, tool_name, arguments[:2000], result_summary[:2000])
            )

    def add_round(self, prompt_tokens: int, completion_tokens: int, total_tokens: int) -> None:
        """记录一轮 LLM 调用的 token 消耗明细。"""
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO rounds (session_id, prompt_tokens, completion_tokens, total_tokens)
                   VALUES (?, ?, ?, ?)""",
                (self.session_id, prompt_tokens, completion_tokens, total_tokens)
            )

    def get_observability_stats(self, pricing: Dict[str, float] = None, limit: int = 10) -> Dict[str, Any]:
        """
        聚合当前会话的可观测性统计：
        - totals：token 总量、轮数、工具调用次数、预估成本
        - tool_call_stats：按工具聚合调用次数
        - recent_tool_calls / recent_rounds：最近明细（时间线）
        pricing 格式：{"prompt": 每千token价格, "completion": 每千token价格}，None 则不估算成本
        """
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT
                     COALESCE(SUM(prompt_tokens), 0)     AS prompt,
                     COALESCE(SUM(completion_tokens), 0) AS completion,
                     COALESCE(SUM(total_tokens), 0)      AS total,
                     COUNT(*)                            AS rounds
                   FROM rounds WHERE session_id = ?""",
                (self.session_id,)
            ).fetchone()

            tool_count = conn.execute(
                "SELECT COUNT(*) AS c FROM tool_calls WHERE session_id = ?",
                (self.session_id,)
            ).fetchone()["c"]

            tool_stats = conn.execute(
                """SELECT tool_name, COUNT(*) AS count, MAX(created_at) AS last_used
                   FROM tool_calls WHERE session_id = ?
                   GROUP BY tool_name ORDER BY count DESC, last_used DESC""",
                (self.session_id,)
            ).fetchall()

            recent_tools = conn.execute(
                """SELECT tool_name, arguments, result_summary, created_at
                   FROM tool_calls WHERE session_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (self.session_id, limit)
            ).fetchall()

            recent_rounds = conn.execute(
                """SELECT prompt_tokens, completion_tokens, total_tokens, created_at
                   FROM rounds WHERE session_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (self.session_id, limit)
            ).fetchall()

        prompt, completion, total = row["prompt"], row["completion"], row["total"]
        cost = None
        if pricing:
            cost = round(
                prompt * pricing.get("prompt", 0) / 1000
                + completion * pricing.get("completion", 0) / 1000,
                6
            )

        return {
            "totals": {
                "prompt_tokens": prompt,
                "completion_tokens": completion,
                "total_tokens": total,
                "rounds": row["rounds"],
                "tool_calls": tool_count,
                "estimated_cost": cost,
            },
            "tool_call_stats": [
                {"tool": r["tool_name"], "count": r["count"], "last_used": r["last_used"]}
                for r in tool_stats
            ],
            "recent_tool_calls": [
                {
                    "tool": r["tool_name"],
                    "arguments": r["arguments"],
                    "result_summary": r["result_summary"],
                    "created_at": r["created_at"],
                }
                for r in recent_tools
            ],
            "recent_rounds": [
                {
                    "prompt_tokens": r["prompt_tokens"],
                    "completion_tokens": r["completion_tokens"],
                    "total_tokens": r["total_tokens"],
                    "created_at": r["created_at"],
                }
                for r in recent_rounds
            ],
        }

    def get_long_term_memory(self) -> str:
        """读取长期记忆（MEMORY.md）"""
        if os.path.exists(self.long_term_file):
            try:
                with open(self.long_term_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return ""

    def save_long_term_memory(self, memory_text: str):
        """保存长期记忆"""
        with open(self.long_term_file, "w", encoding="utf-8") as f:
            f.write(memory_text)

    def clear_history(self):
        """清空当前 session 的对话记录、token 统计、摘要及可观测性明细"""
        self.messages = []
        self.tokens = {"prompt": 0, "completion": 0}
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
            conn.execute("DELETE FROM tokens WHERE session_id = ?", (self.session_id,))
            conn.execute("DELETE FROM tool_calls WHERE session_id = ?", (self.session_id,))
            conn.execute("DELETE FROM rounds WHERE session_id = ?", (self.session_id,))
            conn.execute("DELETE FROM summaries WHERE session_id = ?", (self.session_id,))
