import os
import asyncio
from typing import List, Dict, Any, Optional, Callable

from app.events import emit
from app.workspace.manager import get_workspace_manager
from app.graph.controller import (
    evaluate_next_decision,
    MAX_AUTONOMOUS_ITERATIONS,
    MAX_REPLANS,
    MAX_RECOVERY_ATTEMPTS,
    DECISION_CONTINUE,
    DECISION_RECOVER,
    DECISION_REPLAN,
    DECISION_VALIDATE,
    DECISION_WAIT_FOR_APPROVAL,
    DECISION_COMPLETE,
    DECISION_FAIL
)
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
    on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
    mode: str = "autonomous",
    model_routing: Optional[Dict[str, str]] = None
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
        "mode": mode.lower(),
        "model_routing": model_routing or {},
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
        # Human-in-the-loop approval state
        "approval_required": False,
        "approval_status": "none",
        "approval_request": None,
        "autonomous_iteration_count": 0,
        "replan_count": 0,
        "recovery_attempts": 0
    }
    
    runs_db[run_id]["status"] = "running"
    runs_db[run_id]["state"] = state

    await emit(run_id, "context_loaded", "orchestrator", {
        "workspace": ws_info,
        "mode": mode,
        "conversation_turns": len(state["conversation_context"]),
        "objective": objective
    })
    
    try:
        while state["current_step"] != "end":
            state["autonomous_iteration_count"] += 1

            # Bounded Autonomous Control Decision
            decision, decision_reason = evaluate_next_decision(state)

            if decision == DECISION_FAIL:
                state["status"] = "failed"
                await emit(run_id, "agent_thinking", "controller", {"summary": f"Autonomous Controller Limit: {decision_reason}"})
                break

            if decision == DECISION_WAIT_FOR_APPROVAL:
                state["approval_required"] = True
                await emit(run_id, "agent_thinking", "controller", {"summary": decision_reason})
                break

            if decision == DECISION_REPLAN:
                state["replan_count"] += 1
                await emit(run_id, "agent_thinking", "controller", {"summary": f"Autonomous Re-Plan ({state['replan_count']}/{MAX_REPLANS}): {decision_reason}"})
                state["current_step"] = "orchestrator"
            elif decision == DECISION_RECOVER:
                state["current_step"] = "recovery"
            elif decision == DECISION_VALIDATE:
                if state["current_step"] not in ["validator", "end"]:
                    state["current_step"] = "validator"

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

            # Pause the run when a destructive action requires human approval.
            if (
                state.get("approval_required") is True
                and state.get("approval_status") == "pending"
            ):
                runs_db[run_id]["status"] = "paused"

                await emit(
                    run_id,
                    "approval_required",
                    "executor",
                    {
                        "status": "pending",
                        "request": state.get("approval_request")
                    }
                )

                return

            if current_node_name == "validator" and state["current_step"] == "end":
                break

        last_val = state.get("validation_results", [{}])[-1] if state.get("validation_results") else {}
        is_final_valid = last_val.get("valid", False) if last_val else True
        if state.get("status") == "failed" or not is_final_valid:
            runs_db[run_id]["status"] = "failed"
            await emit(run_id, "run_failed", node="validator", data={"message": last_val.get("reason", "Validation failed")})
        else:
            runs_db[run_id]["status"] = "completed"
            await emit(run_id, "run_completed", data={"final_status": "completed"})

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


async def resume_approved_run(
    run_id: str,
    decision: str,
    runs_db: dict
):
    run = runs_db.get(run_id)

    if not run:
        raise ValueError("Run not found")

    state = run.get("state", {})

    if run.get("status") != "paused":
        raise ValueError("Run is not waiting for approval")

    if not state.get("approval_required"):
        raise ValueError("Run has no pending approval request")

    if state.get("approval_status") != "pending":
        raise ValueError("Approval request is no longer pending")

    approval_request = state.get("approval_request") or {}

    if decision == "reject":
        state["approval_required"] = False
        state["approval_status"] = "rejected"
        state["status"] = "completed"

        state.setdefault("observations", []).append({
            "tool": approval_request.get("tool"),
            "path": approval_request.get("path"),
            "status": "rejected",
            "message": "User rejected the destructive action.",
            "exit_code": 0
        })

        run["state"] = state
        run["status"] = "completed"

        await emit(
            run_id,
            "approval_rejected",
            "executor",
            {
                "status": "rejected",
                "request": approval_request
            }
        )

        await emit(
            run_id,
            "run_completed",
            data={
                "final_status": "rejected"
            }
        )

        return state

    if decision != "approve":
        raise ValueError("Decision must be 'approve' or 'reject'")

    if approval_request.get("tool") != "delete_file":
        raise ValueError("Unsupported approval action")

    target_file = approval_request.get("path")

    if not target_file:
        raise ValueError("Approval request is missing the target path")

    from app.workspace.tools import execute_tool

    await emit(
        run_id,
        "approval_granted",
        "executor",
        {
            "status": "approved",
            "request": approval_request
        }
    )

    await emit(
        run_id,
        "tool_call_started",
        "executor",
        {
            "tool": "delete_file",
            "path": target_file,
            "approved": True
        }
    )

    del_res = await asyncio.to_thread(
        execute_tool,
        "delete_file",
        path=target_file,
        approved=True
    )

    await emit(
        run_id,
        "tool_call_completed",
        "executor",
        del_res
    )

    if not del_res.get("success"):
        state["approval_required"] = False
        state["approval_status"] = "approved"
        state["status"] = "failed"
        state["error"] = {
            "error_type": "DeleteFailed",
            "message": del_res.get("error", "Approved deletion failed."),
            "node": "executor"
        }

        run["state"] = state
        run["status"] = "failed"

        await emit(
            run_id,
            "run_failed",
            "executor",
            state["error"]
        )

        return state

    state["approval_required"] = False
    state["approval_status"] = "approved"
    state["approval_request"] = None

    state.setdefault("observations", []).append({
        "tool": "delete_file",
        "path": target_file,
        "status": "deleted",
        "exit_code": 0
    })

    await emit(
        run_id,
        "file_deleted",
        "executor",
        {
            "path": target_file,
            "status": "deleted"
        }
    )

    state["current_step"] = "validator"
    state["status"] = "running"
    run["state"] = state
    run["status"] = "running"

    # Resume the remaining workflow from the validator.
    while state["current_step"] != "end":
        current_node_name = state["current_step"]

        if current_node_name not in nodes:
            break

        node_fn = nodes[current_node_name]

        await emit(
            run_id,
            "node_started",
            current_node_name,
            {
                "step": current_node_name
            }
        )

        state = await node_fn(state)

        data = {
            "next": state["current_step"]
        }

        if current_node_name == "validator":
            data["validation_results"] = state.get(
                "validation_results",
                []
            )[-1:]

        elif current_node_name == "recovery":
            data["observations"] = state.get(
                "observations",
                []
            )[-3:]

        await emit(
            run_id,
            "node_completed",
            current_node_name,
            data
        )

        run["state"] = state

    run["state"] = state
    run["status"] = "completed"

    await emit(
        run_id,
        "run_completed",
        data={
            "final_status": "completed"
        }
    )

    return state
