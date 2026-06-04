"""
TutorFlow 本地数据库层

基于 SQLite 维护：
- modules:      学习大模块
- subtasks:     模块下的子任务
- conversations: 对话历史
- learning_notes: 学习笔记 / 已掌握知识点
"""

import sqlite3
import os
import threading
from datetime import datetime
from typing import Optional
from config import Config


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS modules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'pending',
    order_index INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS subtasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id   INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    status      TEXT    DEFAULT 'pending',
    order_index INTEGER DEFAULT 0,
    created_at  TEXT    DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS learning_notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subtask_id INTEGER,
    content    TEXT    NOT NULL,
    created_at TEXT    DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (subtask_id) REFERENCES subtasks(id) ON DELETE SET NULL
);
"""


class Database:
    """线程安全的 SQLite 数据库封装"""

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            config = Config()
        self.db_path = config.db_path
        self._lock = threading.Lock()
        self._init_db()

    # ── 内部工具 ────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.executescript(SCHEMA_SQL)
                conn.commit()
            finally:
                conn.close()

    @staticmethod
    def _now() -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── Modules 大模块 ─────────────────────────────────────

    def add_module(self, name: str, description: str = "",
                   order_index: int = 0) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO modules (name, description, order_index)"
                    " VALUES (?, ?, ?)",
                    (name, description, order_index),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def get_all_modules(self) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM modules ORDER BY order_index, id"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_module(self, module_id: int) -> Optional[dict]:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM modules WHERE id=?", (module_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_module_status(self, module_id: int, status: str) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE modules SET status=?, updated_at=? WHERE id=?",
                    (status, self._now(), module_id),
                )
                conn.commit()
            finally:
                conn.close()

    def delete_module(self, module_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM modules WHERE id=?", (module_id,))
                conn.commit()
            finally:
                conn.close()

    def clear_all_modules(self) -> None:
        """清空所有模块及子任务（级联删除）"""
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM modules")
                conn.commit()
            finally:
                conn.close()

    def import_project_modules(self, modules_data: list[dict]) -> int:
        """
        导入 LLM 生成的项目模块结构。

        Args:
            modules_data: [{"name": str, "description": str,
                            "subtasks": [{"name": str, "description": str}, ...]}, ...]

        Returns:
            导入的模块总数
        """
        with self._lock:
            conn = self._get_conn()
            try:
                # 清空现有模块
                conn.execute("DELETE FROM modules")
                count = 0
                for i, mod in enumerate(modules_data):
                    cur = conn.execute(
                        "INSERT INTO modules (name, description, order_index)"
                        " VALUES (?, ?, ?)",
                        (mod["name"], mod.get("description", ""), i),
                    )
                    module_id = cur.lastrowid
                    for j, st in enumerate(mod.get("subtasks", [])):
                        conn.execute(
                            "INSERT INTO subtasks (module_id, name, description,"
                            " order_index) VALUES (?, ?, ?, ?)",
                            (module_id, st["name"],
                             st.get("description", ""), j),
                        )
                    count += 1
                conn.commit()
                return count
            finally:
                conn.close()

    def get_current_module(self) -> Optional[dict]:
        """获取正在进行的模块（优先级：in_progress > 第一个 pending）"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM modules WHERE status='in_progress'"
                " ORDER BY order_index LIMIT 1"
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM modules WHERE status='pending'"
                    " ORDER BY order_index LIMIT 1"
                ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Subtasks 子任务 ────────────────────────────────────

    def add_subtask(self, module_id: int, name: str,
                    description: str = "", order_index: int = 0) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO subtasks (module_id, name, description,"
                    " order_index) VALUES (?, ?, ?, ?)",
                    (module_id, name, description, order_index),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def get_subtasks(self, module_id: int) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM subtasks WHERE module_id=?"
                " ORDER BY order_index, id",
                (module_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_subtask_status(self, subtask_id: int, status: str) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute(
                    "UPDATE subtasks SET status=?, updated_at=? WHERE id=?",
                    (status, self._now(), subtask_id),
                )
                conn.commit()
            finally:
                conn.close()

    def delete_subtask(self, subtask_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM subtasks WHERE id=?", (subtask_id,))
                conn.commit()
            finally:
                conn.close()

    def get_current_subtask(self, module_id: int) -> Optional[dict]:
        """获取模块下正在进行的子任务"""
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM subtasks"
                " WHERE module_id=? AND status='in_progress'"
                " ORDER BY order_index LIMIT 1",
                (module_id,),
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM subtasks"
                    " WHERE module_id=? AND status='pending'"
                    " ORDER BY order_index LIMIT 1",
                    (module_id,),
                ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ── Conversations 对话历史 ─────────────────────────────

    def add_message(self, role: str, content: str) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO conversations (role, content) VALUES (?, ?)",
                    (role, content),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def get_recent_messages(self, limit: int = 50) -> list[dict]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM conversations"
                " ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()

    def clear_conversations(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                conn.execute("DELETE FROM conversations")
                conn.commit()
            finally:
                conn.close()

    # ── Learning Notes 学习笔记 ────────────────────────────

    def add_note(self, content: str, subtask_id: Optional[int] = None) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.execute(
                    "INSERT INTO learning_notes (subtask_id, content)"
                    " VALUES (?, ?)",
                    (subtask_id, content),
                )
                conn.commit()
                return cur.lastrowid
            finally:
                conn.close()

    def get_notes(self, subtask_id: Optional[int] = None) -> list[dict]:
        conn = self._get_conn()
        try:
            if subtask_id is not None:
                rows = conn.execute(
                    "SELECT * FROM learning_notes WHERE subtask_id=?"
                    " ORDER BY id DESC",
                    (subtask_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM learning_notes ORDER BY id DESC"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ── 学习进度摘要（供 LLM 上下文拼装）──────────────────

    def get_progress_summary(self) -> str:
        """
        生成当前学习进度的文本摘要，用于注入 LLM 上下文。
        格式清晰，便于大模型理解当前教学状态。
        """
        parts = []

        modules = self.get_all_modules()
        if not modules:
            return "📚 尚未创建任何学习模块。请先在侧边栏创建你的第一个学习模块。"

        for mod in modules:
            status_icon = {"pending": "⏳", "in_progress": "🔄",
                           "completed": "✅"}.get(mod["status"], "❓")
            parts.append(
                f"{status_icon} 模块: {mod['name']} [{mod['status']}]"
            )
            if mod["description"]:
                parts.append(f"   描述: {mod['description']}")

            subtasks = self.get_subtasks(mod["id"])
            for st in subtasks:
                st_icon = {"pending": "⬜", "in_progress": "🔷",
                           "completed": "✅"}.get(st["status"], "❓")
                parts.append(f"   {st_icon} 子任务: {st['name']} [{st['status']}]")

        # 已掌握的知识
        notes = self.get_notes()
        if notes:
            parts.append("\n📝 已记录的知识要点:")
            for note in notes[:10]:  # 最近10条
                parts.append(f"   • {note['content']}")

        return "\n".join(parts)
