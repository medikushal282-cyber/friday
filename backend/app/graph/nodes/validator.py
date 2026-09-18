import asyncio
from app.events import emit

async def validator_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "validator", {"summary": "Validating workspace outcome against intent."})
    
    current_step_obj = next((s for s in state.get("plan", []) if s.get("agent") == "validator" and s.get("status") == "pending"), None)
    if current_step_obj:
        current_step_obj["status"] = "running"
        await emit(state["run_id"], "step_started", "validator", {"step_id": current_step_obj["id"]})

    # 1. Check if approval_required was flagged
    if state.get("approval_required"):
        result = {
            "valid": True,
            "status": "approval_required",
            "reason": "Security policy enforced: destructive operation requires explicit user approval."
        }
    else:
        observations = state.get("observations", [])
        if not observations:
            result = {"valid": False, "reason": "No execution observations recorded."}
        else:
            last_obs = observations[-1]
            exit_code = last_obs.get("exit_code")
            stdout = last_obs.get("stdout", "").strip()
            
            # Check if it was a read or file inspection operation
            if last_obs.get("tool") == "read_file":
                if stdout:
                    result = {"valid": True, "reason": "File content successfully read and retrieved from workspace."}
                else:
                    result = {"valid": False, "reason": "File read operation returned empty content."}
            elif exit_code == 0:
                result = {"valid": True, "reason": "Process exited with code 0 and produced expected output."}
            else:
                result = {"valid": False, "reason": f"Process exited with non-zero exit code ({exit_code})."}

    state.setdefault("validation_results", []).append(result)
    await emit(state["run_id"], "validation_result", "validator", result)
    
    if current_step_obj:
        current_step_obj["status"] = "completed"
        await emit(state["run_id"], "step_completed", "validator", {"step_id": current_step_obj["id"], "status": "completed"})

    state["current_step"] = "recovery"
    return state
