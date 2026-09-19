import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

def _db_path() -> str:
    configured = os.environ.get("FRAIDAY_KB_PATH")
    if configured:
        return os.path.abspath(configured)
    root = os.environ.get("FRAIDAY_WORKSPACE_ROOT")
    if root:
        return os.path.join(os.path.abspath(root), ".fraiday", "knowledge.db")
    return str(Path(__file__).resolve().parents[3] / ".fraiday" / "knowledge.db")

def _connect():
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            title TEXT,
            url TEXT,
            content TEXT NOT NULL,
            source_type TEXT NOT NULL DEFAULT 'web',
            confidence REAL NOT NULL DEFAULT 0,
            relevance REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_query ON knowledge(query)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_url ON knowledge(url)")
    conn.commit()
    return conn

def _tokens(value: str):
    return set(re.findall(r"[a-zA-Z0-9_]{3,}", (value or "").lower()))

_STOPWORDS = {"what", "does", "how", "can", "the", "and", "for", "are", "is", "was", "were", "this", "that", "with", "from", "into", "about", "please", "tell", "give", "show", "current"}

def _meaningful_tokens(value: str):
    return _tokens(value) - _STOPWORDS

def add_knowledge(query: str, content: str, *, title="", url="",
                  source_type="web", confidence=0.0, relevance=0.0):
    if not content or not content.strip():
        return {"success": False, "error": "Knowledge content is empty."}
    now = datetime.now(timezone.utc).isoformat()
    conn = _connect()
    try:
        cur = conn.execute(
            """INSERT INTO knowledge
               (query,title,url,content,source_type,confidence,relevance,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (query.strip(), title.strip(), url.strip(), content.strip(), source_type,
             max(0.0, min(1.0, float(confidence))),
             max(0.0, min(1.0, float(relevance))), now, now),
        )
        conn.commit()
        return {"success": True, "id": cur.lastrowid, "query": query, "title": title, "url": url}
    finally:
        conn.close()

def search_knowledge(query: str, limit: int = 5, min_score: float = 0.22) -> List[Dict[str, Any]]:
    q = _meaningful_tokens(query)
    if not q:
        return []
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM knowledge ORDER BY updated_at DESC LIMIT 500").fetchall()
    finally:
        conn.close()
    matches = []
    for row in rows:
        text = " ".join([row["query"] or "", row["title"] or "", row["content"] or ""])
        overlap_count = len(q & _meaningful_tokens(text))
        overlap = overlap_count / max(1, len(q))
        if overlap < 0.5 or overlap_count < min(2, len(q)):
            continue
        score = 0.75 * overlap + 0.15 * float(row["relevance"] or 0) + 0.10 * float(row["confidence"] or 0)
        if score >= min_score:
            item = dict(row)
            item["score"] = round(score, 4)
            matches.append(item)
    matches.sort(key=lambda x: (x["score"], x.get("updated_at", "")), reverse=True)
    return matches[:max(1, min(limit, 20))]

def list_knowledge(limit: int = 50):
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM knowledge ORDER BY updated_at DESC LIMIT ?",
            (max(1, min(limit, 200)),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
