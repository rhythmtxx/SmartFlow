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

    def add_tokens(self, prompt_tokens: int, completion_tokens: int):
        """累加 token 消耗"""
        self.tokens["prompt"] += prompt_tokens
        self.tokens["completion"] += completion_tokens
        self._save_tokens_to_db()

    def get_tokens(self) -> Dict[str, int]:
        """获取当前累加的 token 消耗"""
        return self.tokens

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
        """清空当前 session 的对话记录及 token 统计"""
        self.messages = []
        self.tokens = {"prompt": 0, "completion": 0}
        with self._get_conn() as conn:
            conn.execute("DELETE FROM messages WHERE session_id = ?", (self.session_id,))
            conn.execute("DELETE FROM tokens WHERE session_id = ?", (self.session_id,))
