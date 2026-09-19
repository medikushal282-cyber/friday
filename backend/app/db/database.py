import sqlite3
import json
import os
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "fraiday.db")

class Database:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance.init_db()
        return cls._instance

    def _get_connection(self):
        # sqlite3 doesn't like sharing connections across threads by default unless check_same_thread=False
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS workspaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                artifacts TEXT, 
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        ''')
        
        c.execute('''
            CREATE TABLE IF NOT EXISTS terminals (
                id TEXT PRIMARY KEY,
                pid INTEGER,
                command TEXT NOT NULL,
                cwd TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()

    # --- Workspaces ---
    def get_workspaces(self) -> List[Dict]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM workspaces ORDER BY created_at DESC")
        res = [dict(r) for r in cur.fetchall()]
        conn.close()
        return res

    def create_workspace(self, name: str, path: str) -> Dict:
        conn = self._get_connection()
        cur = conn.cursor()
        w_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        cur.execute("INSERT INTO workspaces (id, name, path, created_at) VALUES (?, ?, ?, ?)",
                    (w_id, name, path, created_at))
        conn.commit()
        conn.close()
        return {"id": w_id, "name": name, "path": path, "created_at": created_at}

    # --- Conversations ---
    def get_conversations(self, workspace_id: str) -> List[Dict]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conversations WHERE workspace_id = ? ORDER BY created_at DESC", (workspace_id,))
        res = [dict(r) for r in cur.fetchall()]
        conn.close()
        return res
        
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = cur.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_conversation(self, workspace_id: str, title: str) -> Dict:
        conn = self._get_connection()
        cur = conn.cursor()
        c_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        cur.execute("INSERT INTO conversations (id, workspace_id, title, created_at) VALUES (?, ?, ?, ?)",
                    (c_id, workspace_id, title, created_at))
        conn.commit()
        conn.close()
        return {"id": c_id, "workspace_id": workspace_id, "title": title, "created_at": created_at}

    # --- Messages ---
    def get_messages(self, conversation_id: str) -> List[Dict]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
        res = []
        for r in cur.fetchall():
            d = dict(r)
            if d.get("artifacts"):
                d["artifacts"] = json.loads(d["artifacts"])
            else:
                d["artifacts"] = []
            res.append(d)
        conn.close()
        return res

    def add_message(self, conversation_id: str, role: str, content: str, artifacts: List[Dict] = None) -> Dict:
        conn = self._get_connection()
        cur = conn.cursor()
        m_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        art_str = json.dumps(artifacts) if artifacts else None
        cur.execute("INSERT INTO messages (id, conversation_id, role, content, artifacts, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (m_id, conversation_id, role, content, art_str, created_at))
        conn.commit()
        conn.close()
        return {"id": m_id, "conversation_id": conversation_id, "role": role, "content": content, "artifacts": artifacts or [], "created_at": created_at}

    # --- Terminals ---
    def get_terminals(self) -> List[Dict]:
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM terminals ORDER BY created_at DESC")
        res = [dict(r) for r in cur.fetchall()]
        conn.close()
        return res

    def add_terminal(self, t_id: str, pid: int, command: str, cwd: str, status: str = "running") -> Dict:
        conn = self._get_connection()
        cur = conn.cursor()
        created_at = datetime.utcnow().isoformat()
        cur.execute("INSERT INTO terminals (id, pid, command, cwd, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (t_id, pid, command, cwd, status, created_at))
        conn.commit()
        conn.close()
        return {"id": t_id, "pid": pid, "command": command, "cwd": cwd, "status": status, "created_at": created_at}

    def update_terminal_status(self, t_id: str, status: str):
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE terminals SET status = ? WHERE id = ?", (status, t_id))
        conn.commit()
        conn.close()

db = Database()
