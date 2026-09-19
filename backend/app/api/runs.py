import asyncio
import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from typing import List, Dict, Any, Optional

from app.graph.workflow import execute_run_task, resume_approved_run
from app.events import get_queue
from app.workspace.manager import get_workspace_manager

router = APIRouter(prefix="/runs", tags=["Runs"])

class AttachmentItem(BaseModel):
    name: str
    content: str
    size: Optional[int] = 0

class RunRequest(BaseModel):
    objective: str
    model: Optional[str] = "qwen/qwen3.8-27b"
    provider: Optional[str] = "groq"
    workspace_id: Optional[str] = None
    conversation_id: Optional[str] = None
    attachments: Optional[List[AttachmentItem]] = None

RunRequest.model_rebuild()

class RunResponse(BaseModel):
    run_id: str
    status: str

class ApprovalRequest(BaseModel):
    decision: str

# In-memory storage for active runs and conversation turn history
RUNS_DB: Dict[str, Dict[str, Any]] = {}
SESSION_HISTORY: List[Dict[str, Any]] = []

def get_session_history() -> List[Dict[str, Any]]:
    return SESSION_HISTORY

def append_session_history(entry: Dict[str, Any]):
    SESSION_HISTORY.append(entry)
    # Keep last 10 turns
    if len(SESSION_HISTORY) > 10:
        SESSION_HISTORY.pop(0)

@router.post("/", response_model=RunResponse)
async def create_run(request: RunRequest):
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    selected_model = request.model or "qwen/qwen3.8-27b"
    selected_provider = request.provider or "groq"
    
    # Resolve workspace and conversation session
    ws_id = request.workspace_id
    conv_id = request.conversation_id
    from app.api.sandbox import get_or_create_default_session, get_conversation_memory
    if not ws_id or not conv_id:
        ws_id, conv_id = get_or_create_default_session()
        
    session_memory = get_conversation_memory(ws_id, conv_id)
    recent_context = session_memory.get("recent_messages", [])
    context_summary = session_memory.get("context_summary", "")

    RUNS_DB[run_id] = {
        "run_id": run_id,
        "objective": request.objective,
        "model": selected_model,
        "provider": selected_provider,
        "workspace_id": ws_id,
        "conversation_id": conv_id,
        "status": "pending",
        "state": {}
    }
    
    # Convert attachments to plain dicts for the workflow
    attachments_data = None
    if request.attachments:
        attachments_data = [a.model_dump() for a in request.attachments]

    asyncio.create_task(
        execute_run_task(
            run_id,
            request.objective,
            RUNS_DB,
            recent_context=recent_context,
            session_context_summary=context_summary,
            workspace_id=ws_id,
            conversation_id=conv_id,
            on_complete=append_session_history,
            model=selected_model,
            provider=selected_provider,
            attachments=attachments_data
        )
    )
    
    return {"run_id": run_id, "status": "pending"}

@router.post("/{run_id}/approval", response_model=RunResponse)
@router.post("/{run_id}/approve", response_model=RunResponse)
async def approve_run(run_id: str, request: ApprovalRequest):
    if run_id not in RUNS_DB:
        raise HTTPException(status_code=404, detail="Run not found")

    decision = request.decision.strip().lower()

    if decision not in {"approve", "reject"}:
        raise HTTPException(
            status_code=400,
            detail="Decision must be 'approve' or 'reject'"
        )

    run = RUNS_DB[run_id]

    if run.get("status") != "paused":
        raise HTTPException(
            status_code=409,
            detail="Run is not waiting for approval"
        )

    state = run.get("state", {})

    if not state.get("approval_required"):
        raise HTTPException(
            status_code=409,
            detail="Run has no pending approval request"
        )

    if state.get("approval_status") != "pending":
        raise HTTPException(
            status_code=409,
            detail="Approval request is no longer pending"
        )

    try:
        asyncio.create_task(
            resume_approved_run(
                run_id,
                decision,
                RUNS_DB
            )
        )

        return {
            "run_id": run_id,
            "status": "resuming"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

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
