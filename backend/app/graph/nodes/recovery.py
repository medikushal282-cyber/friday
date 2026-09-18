import asyncio
from app.events import emit

async def recovery_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "recovery", {"summary": "Checking whether recovery action is required."})
    await asyncio.sleep(1)
    
    results = state.get("validation_results", [])
    is_valid = results[-1].get("valid") if results else False
    
    if is_valid:
        obs = {"status": "skipped", "message": "Recovery not required; validation passed."}
    else:
        obs = {"status": "deferred", "message": "Validation failed. Recovery deferred to a future phase."}
        
    state.setdefault("observations", []).append(obs)
    state["current_step"] = "end"
    return state
