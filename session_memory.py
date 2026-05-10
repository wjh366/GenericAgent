"""
跨会话记忆模块
来源: Hermes Agent hermes_state.py
功能: SQLite持久化会话，支持FTS5搜索
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class Session:
    id: str
    user_id: str
    created_at: str
    updated_at: str
    messages: List[Dict]
    metadata: Dict

class SessionMemory:
    """跨会话记忆存储器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "data", "sessions.db")
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                metadata TEXT
            )
        """)
        
        # 创建消息表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """)
        
        # 创建FTS5全文搜索
        try:
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    content, content=messages, content_rowid=id
                )
            """)
        except:
            pass
        
        conn.commit()
        conn.close()
    
    def create_session(self, user_id: str, metadata: Dict = None) -> str:
        """创建新会话"""
        session_id = f"sess_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (id, user_id, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, user_id, now, now, json.dumps(metadata or {})))
        conn.commit()
        conn.close()
        
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """添加消息"""
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, role, content, now))
        
        # 更新会话时间
        cursor.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
        conn.commit()
        conn.close()
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        # 获取消息
        cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY timestamp", 
                      (session_id,))
        messages = [{"role": r["role"], "content": r["content"]} for r in cursor.fetchall()]
        
        conn.close()
        
        return Session(
            id=row["id"],
            user_id=row["user_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            messages=messages,
            metadata=json.loads(row["metadata"] or "{}")
        )
    
    def search(self, query: str, user_id: str = None, limit: int = 10) -> List[Dict]:
        """搜索历史消息"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        sql = """
            SELECT m.session_id, m.role, m.content, m.timestamp, s.user_id
            FROM messages m
            JOIN sessions s ON m.session_id = s.id
            WHERE m.content LIKE ?
        """
        params = [f"%{query}%"]
        
        if user_id:
            sql += " AND s.user_id = ?"
            params.append(user_id)
        
        sql += " ORDER BY m.timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        
        return results
    
    def list_sessions(self, user_id: str = None, limit: int = 20) -> List[Dict]:
        """列出最近会话"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute("""
                SELECT * FROM sessions WHERE user_id = ? 
                ORDER BY updated_at DESC LIMIT ?
            """, (user_id, limit))
        else:
            cursor.execute("SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
        
        results = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return results


# 使用示例
if __name__ == "__main__":
    memory = SessionMemory()
    
    # 创建会话
    session_id = memory.create_session("default_user", {"source": "test"})
    
    # 添加消息
    memory.add_message(session_id, "user", "你好，这是一个测试")
    memory.add_message(session_id, "assistant", "你好！有什么可以帮助你的吗？")
    
    # 获取会话
    session = memory.get_session(session_id)
    print(f"会话: {session.id}")
    for msg in session.messages:
        print(f"  {msg['role']}: {msg['content']}")
    
    # 搜索
    results = memory.search("测试")
    print(f"\n搜索'测试'结果: {len(results)}条")
