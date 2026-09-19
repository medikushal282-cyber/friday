import asyncio
import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from typing import List, Dict, Any

from app.graph.workflow import execute_run_task, resume_approved_run
from app.events import get_queue
from app.workspace.manager import get_workspace_manager

router = APIRouter(prefix="/runs", tags=["Runs"])

class RunRequest(BaseModel):
    objective: str

class RunResponse(BaseModel):
    run_id: str
    status: str

class ApprovalRequest(BaseModel):
    decision: str

class ContinueRequest(BaseModel):
    objective: str

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

def build_continuation_context(previous_run: Dict[str, Any], objective: str) -> Dict[str, Any]:
    state = previous_run.get("state") or {}
    return {
        "previous_run_id": previous_run.get("run_id"),
        "previous_objective": previous_run.get("objective", ""),
        "objective": objective,
        "workspace": state.get("workspace", {}),
        "plan": state.get("plan", []),
        "observations": state.get("observations", []),
        "artifacts": state.get("artifacts", []),
        "relevant_files": [a.get("path") for a in state.get("artifacts", []) if a.get("path")],
        "conversation_context": list(state.get("conversation_context", [])),
    }

@router.post("/", response_model=RunResponse)
async def create_run(request: RunRequest):
    run_id = f"run_{uuid.uuid4().hex[:8]}"
    
    RUNS_DB[run_id] = {
        "run_id": run_id,
        "objective": request.objective,
        "status": "pending",
        "state": {}
    }
    
    # Snapshot of recent conversation context
    recent_context = list(SESSION_HISTORY)
    
    asyncio.create_task(execute_run_task(run_id, request.objective, RUNS_DB, recent_context, append_session_history))
    
    return {"run_id": run_id, "status": "pending"}

@router.post("/{run_id}/continue", response_model=RunResponse)
async def continue_run(run_id: str, request: ContinueRequest):
    previous = RUNS_DB.get(run_id)
    if not previous:
        raise HTTPException(status_code=404, detail="Run not found")
    if not request.objective.strip():
        raise HTTPException(status_code=400, detail="Continuation objective must not be empty")

    context = build_continuation_context(previous, request.objective.strip())
    new_run_id = f"run_{uuid.uuid4().hex[:8]}"
    RUNS_DB[new_run_id] = {
        "run_id": new_run_id,
        "objective": request.objective.strip(),
        "status": "pending",
        "state": {},
        "continuation_of": run_id,
    }
    recent_context = list(SESSION_HISTORY) + [context]
    asyncio.create_task(execute_run_task(
        new_run_id,
        request.objective.strip(),
        RUNS_DB,
        recent_context,
        append_session_history,
        continuation_context=context,
    ))
    return {"run_id": new_run_id, "status": "pending"}

@router.post("/{run_id}/approval", response_model=RunResponse)
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
