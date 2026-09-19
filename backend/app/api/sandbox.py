import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/sandbox", tags=["Sandbox"])

def get_sandbox_root() -> Path:
    """Get the sandbox directory inside the project root."""
    # backend/app/api/sandbox.py -> go up 3 levels to project root
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


# --- Workspace Endpoints ---

@router.get("/workspaces")
def list_workspaces():
    """List all sandbox workspaces."""
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
    """Create a new sandbox workspace."""
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
    """Delete a sandbox workspace."""
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
    """List conversations within a workspace."""
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
                    "message_count": len(data.get("messages", []))
                })
            except Exception:
                conversations.append({"id": f.stem, "title": f.stem, "created_at": "", "message_count": 0})

    return {"conversations": conversations, "workspace_id": ws_id}


@router.post("/workspaces/{ws_id}/conversations")
def create_conversation(ws_id: str, req: CreateConversationRequest):
    """Create a new conversation in a workspace."""
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
        "messages": []
    }
    (conv_dir / f"{conv_id}.json").write_text(json.dumps(conv_data, indent=2), encoding="utf-8")

    return {"success": True, "conversation": conv_data}


@router.get("/workspaces/{ws_id}/conversations/{conv_id}")
def get_conversation(ws_id: str, conv_id: str):
    """Get a specific conversation's data."""
    sandbox = get_sandbox_root()
    conv_file = sandbox / ws_id / "conversations" / f"{conv_id}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail=f"Conversation '{conv_id}' not found in workspace '{ws_id}'")

    data = json.loads(conv_file.read_text(encoding="utf-8"))
    return data
