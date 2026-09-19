from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.db.database import db

router = APIRouter(prefix="/conversations", tags=["conversations"])

class CreateConversationRequest(BaseModel):
    workspace_id: str
    title: str

class MessageRequest(BaseModel):
    role: str
    content: str
    artifacts: Optional[List[Dict[str, Any]]] = None

@router.get("/workspace/{workspace_id}")
def get_conversations(workspace_id: str):
    return db.get_conversations(workspace_id)

@router.post("")
def create_conversation(req: CreateConversationRequest):
    return db.create_conversation(req.workspace_id, req.title)

@router.get("/{conversation_id}")
def get_conversation(conversation_id: str):
    c = db.get_conversation(conversation_id)
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return c

@router.get("/{conversation_id}/messages")
def get_messages(conversation_id: str):
    return db.get_messages(conversation_id)

@router.post("/{conversation_id}/messages")
def add_message(conversation_id: str, req: MessageRequest):
    return db.add_message(conversation_id, req.role, req.content, req.artifacts)
