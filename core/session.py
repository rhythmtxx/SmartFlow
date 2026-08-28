"""
会话管理器（Multi-Session Manager）。

职责：
1. 全局共享无状态组件（LLM client / skills / knowledge / tools），只构建一次
2. 按 session_id 隔离有状态组件（MemoryStore / ApprovalManager），懒创建
3. 提供每会话的 asyncio.Lock，保证同一会话的并发请求串行
4. 审批跨会话路由：/api/approve 通过 session_id 定位到正确的 ApprovalManager
5. 会话列表聚合（从 SQLite 统计）与删除

设计要点：
- TinyAgent 拆成「共享外壳 + 会话状态」两层：
  共享外壳 = build_shared() 返回的 dict（无状态/只读）
  会话状态 = MemoryStore(session_id=...) + ApprovalManager
- 数据库层面（SQLite messages/tokens 表）从设计之初就带 session_id 列，
  因此本模块只做组装层改造，不动表结构。
"""
import asyncio
import os
import sqlite3
from typing import Dict, Optional, List

from .agent import TinyAgent

# 会话 ID 允许的字符集（用于 DELETE 路径参数校验）
_SESSION_ID_RE = "^[a-zA-Z0-9_-]{1,64}$"


class SessionManager:
    def __init__(self, workspace_dir: str, openai_api_key: str = None,
                 base_url: str = None, model: str = "gpt-4o-mini",
                 pricing: Optional[Dict] = None):
        self.workspace_dir = workspace_dir
        self.openai_api_key = openai_api_key
        self.base_url = base_url
        self.model = model
        # 成本估算价格：{"prompt": 每千token元, "completion": 每千token元}
        self.pricing = pricing or {}

        self._shared: Optional[Dict] = None
        self._sessions: Dict[str, TinyAgent] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    # ------------------------------------------------------------------ #
    # 共享组件                                                             #
    # ------------------------------------------------------------------ #

    def shared_components(self) -> Dict:
        """获取全局共享组件（懒构建一次）。"""
        if self._shared is None:
            self._shared = TinyAgent.build_shared(
                self.workspace_dir, self.openai_api_key, self.base_url, self.model
            )
        return self._shared

    # ------------------------------------------------------------------ #
    # 会话生命周期                                                          #
    # ------------------------------------------------------------------ #

    def get(self, session_id: str = "default") -> TinyAgent:
        """获取（或懒创建）指定会话的 Agent。"""
        if session_id not in self._sessions:
            agent = TinyAgent(
                self.workspace_dir,
                session_id=session_id,
                shared=self.shared_components(),
                model=self.model,
            )
            self._sessions[session_id] = agent
            self._locks[session_id] = asyncio.Lock()
        return self._sessions[session_id]

    def lock(self, session_id: str = "default") -> asyncio.Lock:
        """获取指定会话的串行锁（同一会话的并发请求必须串行）。"""
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def clear(self, session_id: str = "default"):
        """清空指定会话的记忆。"""
        agent = self._sessions.get(session_id)
        if agent:
            agent.clear_memory()

    def delete(self, session_id: str) -> bool:
        """
        删除指定会话：移除内存实例 + 删除 SQLite 中的会话数据。
        返回是否成功删除（不存在返回 False）。
        """
        self._sessions.pop(session_id, None)
        self._locks.pop(session_id, None)

        db_path = os.path.join(self.workspace_dir, "memory", "memory.db")
        if not os.path.exists(db_path):
            return False
        try:
            with sqlite3.connect(db_path, check_same_thread=False) as conn:
                cur = conn.execute(
                    "DELETE FROM messages WHERE session_id = ?", (session_id,)
                )
                conn.execute("DELETE FROM tokens WHERE session_id = ?", (session_id,))
                return cur.rowcount > 0
        except sqlite3.Error:
            return False

    def list_sessions(self) -> List[Dict]:
        """聚合所有会话的统计：session_id、消息数、最后活跃时间。"""
        db_path = os.path.join(self.workspace_dir, "memory", "memory.db")
        sessions: List[Dict] = []
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path, check_same_thread=False)
                try:
                    rows = conn.execute(
                        """SELECT session_id, COUNT(*) as cnt, MAX(created_at) as last
                           FROM messages GROUP BY session_id ORDER BY last DESC"""
                    ).fetchall()
                    sessions = [
                        {
                            "session_id": r[0],
                            "message_count": r[1],
                            "last_active": r[2],
                        }
                        for r in rows
                    ]
                finally:
                    conn.close()
            except sqlite3.Error:
                sessions = []

        # 合并内存中已创建但还没有任何消息的会话
        # （GROUP BY 聚合不会出现消息数为 0 的会话，但新建的空会话应该可见）
        seen = {s["session_id"] for s in sessions}
        for session_id in self._sessions:
            if session_id not in seen:
                sessions.append({
                    "session_id": session_id,
                    "message_count": 0,
                    "last_active": None,
                })
        return sessions

    # ------------------------------------------------------------------ #
    # 审批跨会话路由                                                        #
    # ------------------------------------------------------------------ #

    def resolve_approval(self, session_id: str, approval_id: str, approved: bool) -> bool:
        """
        按会话路由审批结果。
        返回 False 表示会话不存在，或审批请求不存在/已超时。
        """
        agent = self._sessions.get(session_id)
        if agent is None:
            return False
        return agent.resolve_approval(approval_id, approved)

    # ------------------------------------------------------------------ #
    # 状态聚合（供 /api/status 使用）                                       #
    # ------------------------------------------------------------------ #

    def get_status(self) -> Dict:
        """技能与工具清单（全局共享组件，与会话无关）。"""
        shared = self.shared_components()
        shared["skills"].load_all_skills()  # Dynamic reload
        return {
            "skills": shared["skills"].get_skills_summary(),
            "tools": [
                {"name": t.name, "description": t.description}
                for t in shared["tools"].tools.values()
            ],
        }

    # ------------------------------------------------------------------ #
    # 可观测性统计（供 /api/stats 使用）                                     #
    # ------------------------------------------------------------------ #

    def get_stats(self, session_id: str = "default") -> Dict:
        """获取指定会话的可观测性统计（token 明细、成本估算、工具调用时间线）。"""
        agent = self.get(session_id)
        return agent.memory.get_observability_stats(pricing=self.pricing)
