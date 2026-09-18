import asyncio
import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uuid
from typing import List, Dict, Any

from app.graph.workflow import execute_run_task
from app.events import get_queue
from app.workspace.manager import get_workspace_manager

router = APIRouter(prefix="/runs", tags=["Runs"])

class RunRequest(BaseModel):
    objective: str

class RunResponse(BaseModel):
    run_id: str
    status: str

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
