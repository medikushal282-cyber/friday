import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])

def get_sandbox_root() -> Path:
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    sandbox_dir = project_root / "sandbox"
    sandbox_dir.mkdir(exist_ok=True)
    return sandbox_dir


# --- Models ---

class CreateWorkspaceRequest(BaseModel):
    name: str
    description: Optional[str] = ""

class CreateConversationRequest(BaseModel):
    title: str

class AppendMessageRequest(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str
    metadata: Optional[dict] = None


# --- Workspace Endpoints ---

@router.get("/workspaces")
def list_workspaces():
    sandbox = get_sandbox_root()
    workspaces = []
    for entry in sorted(sandbox.iterdir()):
        if entry.is_dir():
            meta_file = entry / "workspace.json"
            meta = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            conv_dir = entry / "conversations"
            conv_count = 0
            if conv_dir.exists():
                conv_count = len([f for f in conv_dir.iterdir() if f.is_file() and f.suffix == ".json"])
            workspaces.append({
                "id": entry.name,
                "name": meta.get("name", entry.name),
                "description": meta.get("description", ""),
                "created_at": meta.get("created_at", ""),
                "conversation_count": conv_count
            })
    return {"workspaces": workspaces}


@router.post("/workspaces")
def create_workspace(req: CreateWorkspaceRequest):
    sandbox = get_sandbox_root()
    ws_id = req.name.lower().replace(" ", "_").replace("-", "_")
    ws_dir = sandbox / ws_id
    if ws_dir.exists():
        ws_id = f"{ws_id}_{uuid.uuid4().hex[:6]}"
        ws_dir = sandbox / ws_id

    ws_dir.mkdir(parents=True, exist_ok=True)
    (ws_dir / "conversations").mkdir(exist_ok=True)
    (ws_dir / "artifacts").mkdir(exist_ok=True)

    meta = {
        "id": ws_id,
        "name": req.name,
        "description": req.description or "",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "root_path": str(ws_dir)
    }
    (ws_dir / "workspace.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"success": True, "workspace": meta}


@router.delete("/workspaces/{ws_id}")
def delete_workspace(ws_id: str):
    sandbox = get_sandbox_root()
    ws_dir = sandbox / ws_id
    if not ws_dir.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{ws_id}' not found")
    import shutil
    shutil.rmtree(ws_dir)
    return {"success": True, "deleted": ws_id}


# --- Conversation Endpoints ---

@router.get("/workspaces/{ws_id}/conversations")
def list_conversations(ws_id: str):
    sandbox = get_sandbox_root()
    conv_dir = sandbox / ws_id / "conversations"
    if not conv_dir.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{ws_id}' not found")

    conversations = []
    for f in sorted(conv_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file() and f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                conversations.append({
                    "id": f.stem,
                    "title": data.get("title", f.stem),
                    "created_at": data.get("created_at", ""),
                    "message_count": len(data.get("messages", [])),
                    "context_summary": data.get("context_summary", "")
                })
            except Exception:
                conversations.append({"id": f.stem, "title": f.stem, "created_at": "", "message_count": 0})

    return {"conversations": conversations, "workspace_id": ws_id}


@router.post("/workspaces/{ws_id}/conversations")
def create_conversation(ws_id: str, req: CreateConversationRequest):
    sandbox = get_sandbox_root()
    ws_dir = sandbox / ws_id
    if not ws_dir.exists():
        raise HTTPException(status_code=404, detail=f"Workspace '{ws_id}' not found")

    conv_dir = ws_dir / "conversations"
    conv_dir.mkdir(exist_ok=True)

    conv_id = f"conv_{uuid.uuid4().hex[:8]}"
    conv_data = {
        "id": conv_id,
        "title": req.title,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "messages": [],
        "context_summary": ""
    }
    (conv_dir / f"{conv_id}.json").write_text(json.dumps(conv_data, indent=2), encoding="utf-8")
    return {"success": True, "conversation": conv_data}


@router.get("/workspaces/{ws_id}/conversations/{conv_id}")
def get_conversation(ws_id: str, conv_id: str):
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")
    return json.loads(conv_file.read_text(encoding="utf-8"))


@router.delete("/workspaces/{ws_id}/conversations/{conv_id}")
def delete_conversation(ws_id: str, conv_id: str):
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")
    conv_file.unlink()
    return {"success": True, "deleted": conv_id}


@router.post("/workspaces/{ws_id}/conversations/{conv_id}/messages")
def append_message(ws_id: str, conv_id: str, req: AppendMessageRequest):
    """Append a message to a conversation and auto-update context summary."""
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")

    data = json.loads(conv_file.read_text(encoding="utf-8"))
    msg = {
        "role": req.role,
        "content": req.content,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": req.metadata or {}
    }
    data["messages"].append(msg)

    # Auto-summarize context every 6 messages using a small/fast model
    if len(data["messages"]) % 6 == 0:
        data["context_summary"] = _summarize_context(data["messages"])

    conv_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"success": True, "message_count": len(data["messages"])}


@router.get("/workspaces/{ws_id}/conversations/{conv_id}/context")
def get_context(ws_id: str, conv_id: str):
    """Get the context summary for a conversation, generating if needed."""
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found")

    data = json.loads(conv_file.read_text(encoding="utf-8"))
    messages = data.get("messages", [])

    if not messages:
        return {"context_summary": "", "message_count": 0}

    # Regenerate if stale
    summary = data.get("context_summary", "")
    if not summary and len(messages) >= 2:
        summary = _summarize_context(messages)
        data["context_summary"] = summary
        conv_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return {"context_summary": summary, "message_count": len(messages)}


def _summarize_context(messages: List[dict]) -> str:
    """Use a small fast model (llama-3.1-8b-instant or gpt-oss-20b) to compress conversation into token-efficient context memory."""
    if not messages:
        return ""
    try:
        from app.llm.router import call_llm

        # Build a compact transcript
        transcript_lines = []
        for m in messages[-16:]:  # Last 16 messages max
            role = m.get("role", "?").upper()
            content = m.get("content", "")[:250]  # Truncate long messages to save tokens
            transcript_lines.append(f"{role}: {content}")
        transcript = "\n".join(transcript_lines)

        system_prompt = (
            "You are a compact context memory compressor for an AI software engineering assistant. "
            "Given a conversation transcript, produce a dense, concise summary (under 100 words) "
            "capturing: 1) Core user goals, 2) Key files/features created, 3) Current state and pending tasks. "
            "Be purely factual and token-efficient. Do NOT include conversational filler."
        )

        # Try fast small model on Groq
        for fast_model in ["llama-3.1-8b-instant", "openai/gpt-oss-20b"]:
            try:
                summary, _ = call_llm(
                    system=system_prompt,
                    user=f"Compress this conversation into concise memory:\n\n{transcript}",
                    model=fast_model,
                    provider="groq"
                )
                if summary and summary.strip():
                    return summary.strip()[:400]
            except Exception:
                continue

        raise RuntimeError("Groq small model summarization unavailable")
    except Exception:
        # High-efficiency fallback heuristic
        recent = messages[-4:]
        parts = []
        for m in recent:
            role = m.get("role", "?")
            content = m.get("content", "")[:80].replace("\n", " ")
            parts.append(f"{role}: {content}")
        return "Recent turns: " + " | ".join(parts)


def get_or_create_default_session() -> tuple[str, str]:
    """Ensures at least one sandbox workspace and conversation exist, returns (ws_id, conv_id)."""
    sandbox = get_sandbox_root()
    ws_id = "default"
    ws_dir = sandbox / ws_id
    if not ws_dir.exists():
        ws_dir.mkdir(parents=True, exist_ok=True)
        (ws_dir / "conversations").mkdir(exist_ok=True)
        meta = {
            "id": ws_id,
            "name": "Default Workspace",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "root_path": str(ws_dir)
        }
        (ws_dir / "workspace.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    conv_dir = ws_dir / "conversations"
    conv_dir.mkdir(exist_ok=True)
    conv_files = list(conv_dir.glob("*.json"))
    if conv_files:
        return ws_id, conv_files[0].stem

    conv_id = "conv_default"
    conv_data = {
        "id": conv_id,
        "title": "General Conversation",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "messages": [],
        "context_summary": ""
    }
    (conv_dir / f"{conv_id}.json").write_text(json.dumps(conv_data, indent=2), encoding="utf-8")
    return ws_id, conv_id


def get_conversation_memory(ws_id: str, conv_id: str) -> dict:
    """Returns persistent context memory and recent messages for this session."""
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        return {"context_summary": "", "recent_messages": []}

    try:
        data = json.loads(conv_file.read_text(encoding="utf-8"))
        messages = data.get("messages", [])
        summary = data.get("context_summary", "")
        if not summary and len(messages) >= 2:
            summary = _summarize_context(messages)
            data["context_summary"] = summary
            conv_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return {
            "context_summary": summary,
            "recent_messages": messages[-4:]  # Only last 4 messages for token efficiency
        }
    except Exception:
        return {"context_summary": "", "recent_messages": []}


def save_conversation_turn(ws_id: str, conv_id: str, user_text: str, assistant_text: str, metadata: dict = None) -> str:
    """Appends user and assistant messages to session and updates context memory via small model."""
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        return ""

    try:
        data = json.loads(conv_file.read_text(encoding="utf-8"))
        now = datetime.utcnow().isoformat() + "Z"
        if user_text:
            data["messages"].append({
                "role": "user",
                "content": user_text,
                "timestamp": now,
                "metadata": {}
            })
        if assistant_text:
            data["messages"].append({
                "role": "assistant",
                "content": assistant_text,
                "timestamp": now,
                "metadata": metadata or {}
            })

        # Compress context memory using small model
        summary = _summarize_context(data["messages"])
        data["context_summary"] = summary
        conv_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return summary
    except Exception as e:
        print(f"Failed to save conversation turn: {e}")
        return ""

