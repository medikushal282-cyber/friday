import asyncio
import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from typing import List, Dict, Any, Optional

from app.graph.workflow import execute_run_task
from app.events import get_queue
from app.workspace.manager import get_workspace_manager

router = APIRouter(prefix="/runs", tags=["Runs"])
conversations_router = APIRouter(prefix="/conversations", tags=["Conversations"])

class RunRequest(BaseModel):
    objective: str
    conversation_id: Optional[str] = None
    context: Optional[List[Dict[str, Any]]] = None

class RunResponse(BaseModel):
    run_id: str
    conversation_id: str
    status: str

# In-memory storage for active runs and conversation sessions
RUNS_DB: Dict[str, Dict[str, Any]] = {}
CONVERSATIONS_DB: Dict[str, Dict[str, Any]] = {}
SESSION_HISTORY: List[Dict[str, Any]] = []

def get_session_history() -> List[Dict[str, Any]]:
    return SESSION_HISTORY

def append_session_history(entry: Dict[str, Any]):
    SESSION_HISTORY.append(entry)
    if len(SESSION_HISTORY) > 10:
        SESSION_HISTORY.pop(0)

@router.post("/", response_model=RunResponse)
async def create_run(request: RunRequest):
    conv_id = request.conversation_id
    if not conv_id or conv_id not in CONVERSATIONS_DB:
        conv_id = f"conv_{uuid.uuid4().hex[:8]}"
        CONVERSATIONS_DB[conv_id] = {
            "conversation_id": conv_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "messages": [],
            "history": [],
            "runs": []
        }

    run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    RUNS_DB[run_id] = {
        "run_id": run_id,
        "conversation_id": conv_id,
        "objective": request.objective,
        "status": "pending",
        "state": {}
    }
    CONVERSATIONS_DB[conv_id]["runs"].append(run_id)

    # Record user message in conversation messages
    user_msg = {
        "message_id": f"msg_{uuid.uuid4().hex[:8]}",
        "role": "user",
        "content": request.objective,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }
    CONVERSATIONS_DB[conv_id]["messages"].append(user_msg)

    # Determine context to pass to workflow (explicit context list or conversation history)
    conv_context = request.context if request.context is not None else list(CONVERSATIONS_DB[conv_id]["history"])

    def on_run_complete(entry: Dict[str, Any]):
        append_session_history(entry)
        if conv_id in CONVERSATIONS_DB:
            CONVERSATIONS_DB[conv_id]["history"].append(entry)
            if len(CONVERSATIONS_DB[conv_id]["history"]) > 10:
                CONVERSATIONS_DB[conv_id]["history"].pop(0)
            
            asst_msg = {
                "message_id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": "assistant",
                "run_id": run_id,
                "objective": request.objective,
                "entry": entry,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            CONVERSATIONS_DB[conv_id]["messages"].append(asst_msg)

    asyncio.create_task(execute_run_task(run_id, request.objective, RUNS_DB, conv_context, on_run_complete))
    
    return {"run_id": run_id, "conversation_id": conv_id, "status": "pending"}

@router.get("/{run_id}/events")
async def stream_run_events(run_id: str):
    if run_id not in RUNS_DB:
        raise HTTPException(status_code=404, detail="Run not found")
        
    async def event_generator():
        q = get_queue(run_id)
        while True:
            event = await q.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event["event"] in ["run_completed", "run_failed"]:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/{run_id}")
async def get_run(run_id: str):
    if run_id not in RUNS_DB:
        raise HTTPException(status_code=404, detail="Run not found")
    return RUNS_DB[run_id]

# Conversation Endpoints
@conversations_router.get("/")
async def list_conversations():
    result = []
    for conv_id, conv in CONVERSATIONS_DB.items():
        last_obj = ""
        user_msgs = [m for m in conv.get("messages", []) if m.get("role") == "user"]
        if user_msgs:
            last_obj = user_msgs[-1].get("content", "")
        result.append({
            "conversation_id": conv_id,
            "created_at": conv.get("created_at"),
            "run_count": len(conv.get("runs", [])),
            "message_count": len(conv.get("messages", [])),
            "last_objective": last_obj
        })
    return result

@conversations_router.get("/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id not in CONVERSATIONS_DB:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return CONVERSATIONS_DB[conversation_id]
