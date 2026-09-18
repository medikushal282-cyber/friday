import os
import asyncio
from typing import List, Dict, Any, Optional, Callable

from app.events import emit
from app.workspace.manager import get_workspace_manager
from app.graph.nodes.orchestrator import orchestrator_node
from app.graph.nodes.researcher import researcher_node
from app.graph.nodes.executor import executor_node
from app.graph.nodes.validator import validator_node
from app.graph.nodes.recovery import recovery_node

nodes = {
    "orchestrator": orchestrator_node,
    "researcher": researcher_node,
    "executor": executor_node,
    "validator": validator_node,
    "recovery": recovery_node
}

def sanitize_error_message(msg: str) -> str:
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key and groq_key in msg:
        msg = msg.replace(groq_key, "[REDACTED_API_KEY]")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if openrouter_key and openrouter_key in msg:
        msg = msg.replace(openrouter_key, "[REDACTED_API_KEY]")
    return msg

async def execute_run_task(
    run_id: str,
    objective: str,
    runs_db: dict,
    recent_context: Optional[List[Dict[str, Any]]] = None,
    on_complete: Optional[Callable[[Dict[str, Any]], None]] = None
):
    ws = get_workspace_manager()
    ws_info = {
        "workspace_id": ws.workspace_id,
        "name": ws.name,
        "root_path": ws.root_path
    }

    state = {
        "run_id": run_id,
        "objective": objective,
        "workspace": ws_info,
        "conversation_context": recent_context or [],
        "plan": [],
        "current_step": "orchestrator",
        "research": [],
        "tool_calls": [],
        "observations": [],
        "artifacts": [],
        "validation_results": [],
        "status": "started",
        "error": None,
        "retry_count": 0,
        "approval_required": False
    }
    
    runs_db[run_id]["status"] = "running"
    runs_db[run_id]["state"] = state

    # Step 7: Emit context_loaded
    await emit(run_id, "context_loaded", "orchestrator", {
        "workspace": ws_info,
        "conversation_turns": len(state["conversation_context"]),
        "objective": objective
    })
    
    try:
        while state["current_step"] != "end":
            current_node_name = state["current_step"]
            if current_node_name not in nodes:
                break
                
            node_fn = nodes[current_node_name]
            
            await emit(run_id, "node_started", current_node_name, {"step": current_node_name})
            
            state = await node_fn(state)
            
            data = {"next": state["current_step"]}
            if current_node_name == "orchestrator":
                data["plan"] = state.get("plan")
            elif current_node_name == "researcher":
                data["research"] = state.get("research")
            elif current_node_name == "executor":
                data["observations"] = state.get("observations", [])[-3:]
                data["artifacts"] = state.get("artifacts", [])
            elif current_node_name == "validator":
                data["validation_results"] = state.get("validation_results", [])[-1:]
                
            await emit(run_id, "node_completed", current_node_name, data)
            
            runs_db[run_id]["state"] = state
            
        runs_db[run_id]["status"] = "completed"
        await emit(run_id, "run_completed", data={"final_status": "completed"})

        # Save turn to session history for follow-up turns
        if on_complete:
            on_complete({
                "run_id": run_id,
                "objective": objective,
                "artifacts": state.get("artifacts", []),
                "observations": state.get("observations", [])[-2:] if state.get("observations") else [],
                "validation": state.get("validation_results", [])[-1:] if state.get("validation_results") else []
            })
        
    except Exception as e:
        runs_db[run_id]["status"] = "failed"
        current_node_name = state.get("current_step", "unknown")
        safe_msg = sanitize_error_message(str(e))
        error_payload = {
            "error_type": type(e).__name__,
            "message": safe_msg,
            "node": current_node_name
        }
        runs_db[run_id]["state"]["error"] = error_payload
        await emit(run_id, "run_failed", node=current_node_name, data=error_payload)
