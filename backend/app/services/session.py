# ============================================================
# Soul Companion - 会话管理 (SQLite 持久化)
# ============================================================
import time
import uuid
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import aiosqlite

from ..config import SESSION_EXPIRE_HOURS, MAX_CONTEXT_MESSAGES

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "sessions.db"


@dataclass
class Message:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    session_id: str
    user_id: str
    messages: List[Message] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    companion_name: str = "小暖"


class SessionManager:
    """SQLite 持久化会话管理"""

    def __init__(self, expire_hours: int = 72, max_context: int = 30):
        self.expire_seconds = expire_hours * 3600
        self.max_context = max_context
        self._ready = False

    async def _ensure_db(self):
        """延迟初始化数据库"""
        if self._ready:
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    user_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_active REAL NOT NULL,
                    companion_name TEXT DEFAULT '小暖'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            await db.execute("CREATE INDEX IF NOT EXISTS idx_msg_user ON messages(user_id, timestamp)")
            await db.commit()
        self._ready = True

    async def get_or_create(self, user_id: str, companion_name: str = "小暖") -> Session:
        await self._ensure_db()
        await self._cleanup()

        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT session_id, created_at, last_active, companion_name FROM sessions WHERE user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            now = time.time()

            if row:
                await db.execute(
                    "UPDATE sessions SET last_active = ? WHERE user_id = ?",
                    (now, user_id)
                )
                await db.commit()
                session = Session(
                    session_id=row[0],
                    user_id=user_id,
                    created_at=row[1],
                    last_active=now,
                    companion_name=row[3] or companion_name
                )
            else:
                sid = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO sessions (user_id, session_id, created_at, last_active, companion_name) VALUES (?,?,?,?,?)",
                    (user_id, sid, now, now, companion_name)
                )
                await db.commit()
                session = Session(
                    session_id=sid,
                    user_id=user_id,
                    created_at=now,
                    last_active=now,
                    companion_name=companion_name
                )

        # 加载消息
        session.messages = await self._load_messages(user_id)
        return session

    async def _load_messages(self, user_id: str) -> List[Message]:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT role, content, timestamp FROM messages WHERE user_id = ? ORDER BY timestamp ASC",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [Message(role=r[0], content=r[1], timestamp=r[2]) for r in rows]

    async def add_message(self, user_id: str, role: str, content: str):
        await self._ensure_db()
        now = time.time()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT INTO messages (user_id, role, content, timestamp) VALUES (?,?,?,?)",
                (user_id, role, content, now)
            )
            # 保持上下文窗口
            await db.execute("""
                DELETE FROM messages WHERE user_id = ? AND id NOT IN (
                    SELECT id FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?
                )
            """, (user_id, user_id, self.max_context))
            await db.execute(
                "UPDATE sessions SET last_active = ? WHERE user_id = ?",
                (now, user_id)
            )
            await db.commit()

    async def get_context(self, user_id: str) -> List[dict]:
        await self._ensure_db()
        messages = await self._load_messages(user_id)
        return [{"role": m.role, "content": m.content} for m in messages]

    async def clear(self, user_id: str):
        await self._ensure_db()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            await db.commit()

    async def _cleanup(self):
        """清理过期会话"""
        cutoff = time.time() - self.expire_seconds
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute("SELECT user_id FROM sessions WHERE last_active < ?", (cutoff,))
            expired = [row[0] for row in await cursor.fetchall()]
            for uid in expired:
                await db.execute("DELETE FROM messages WHERE user_id = ?", (uid,))
                await db.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
            if expired:
                await db.commit()
                logger.info(f"Cleaned up {len(expired)} expired sessions")

    async def get_all_sessions(self) -> List[dict]:
        """获取所有活跃会话（管理用）"""
        await self._ensure_db()
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT user_id, session_id, created_at, last_active, companion_name FROM sessions ORDER BY last_active DESC"
            )
            rows = await cursor.fetchall()
            return [
                {"user_id": r[0], "session_id": r[1], "created_at": r[2], "last_active": r[3], "companion_name": r[4]}
                for r in rows
            ]


# 全局实例
session_manager = SessionManager()
