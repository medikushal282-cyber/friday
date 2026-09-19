import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import get_workspace_manager
from app.graph.workflow import execute_run_task

async def run_activity2_portal_verification():
    print("==================================================")
    print("ACTIVITY 2 — CONTEXT & MEMORY PORTAL VERIFICATION")
    print("==================================================")

    ws = get_workspace_manager()
    # Clean up any pre-existing context_test.py
    try:
        ws.delete_file("context_test.py")
    except Exception:
        pass

    # STEP 1: Turn 1 - Initial Creation
    run_id1 = "act2_run_001"
    obj1 = "Create context_test.py that prints Hello Fraiday."
    runs_db = {run_id1: {"run_id": run_id1, "objective": obj1, "status": "pending", "state": {}}}

    print(f"\n--- TURN 1: {obj1} ---")
    await execute_run_task(run_id1, obj1, runs_db)

    state1 = runs_db[run_id1]["state"]
    status1 = runs_db[run_id1]["status"]
    print("Turn 1 Status:", status1)
    assert status1 == "completed"

    obs1 = next(o for o in reversed(state1.get("observations", [])) if "exit_code" in o)
    print("Turn 1 Output:", obs1.get("stdout", "").strip())
    assert "Hello Fraiday" in obs1.get("stdout", "")

    # Save Turn 1 history into conversation context
    turn1_history = [{
        "run_id": run_id1,
        "objective": obj1,
        "artifacts": state1.get("artifacts", []),
        "observations": state1.get("observations", []),
        "validation": state1.get("validation_results", [])
    }]

    # STEP 2: Turn 2 - Follow-up Instruction
    run_id2 = "act2_run_002"
    obj2 = "Update it to print Hello Fraiday 2."
    runs_db[run_id2] = {"run_id": run_id2, "objective": obj2, "status": "pending", "state": {}}

    print(f"\n--- TURN 2 (FOLLOW-UP): {obj2} ---")
    await execute_run_task(run_id2, obj2, runs_db, recent_context=turn1_history)

    state2 = runs_db[run_id2]["state"]
    status2 = runs_db[run_id2]["status"]
    print("Turn 2 Status:", status2)
    assert status2 == "completed"

    # Verify tool calls in Turn 2 used UPDATE_FILE
    tools_used = [c.get("action", {}).get("tool") for c in state2.get("tool_calls", [])]
    print("Turn 2 Tools Used:", tools_used)
    assert "update_file" in tools_used, f"Expected update_file, got {tools_used}"

    obs2 = next(o for o in reversed(state2.get("observations", [])) if "exit_code" in o)
    stdout2 = obs2.get("stdout", "").strip()
    print("Turn 2 Execution Output:\n", stdout2)
    assert "Hello Fraiday 2" in stdout2, f"Expected 'Hello Fraiday 2', got '{stdout2}'"

    val_res = state2.get("validation_results", [{}])[-1]
    assert val_res.get("valid") is True, f"Validation failed: {val_res}"

    print("\n==================================================")
    print("ACTIVITY 2 PORTAL VERIFICATION PASSED SUCCESSFULLY!")
    print("Turn 1 -> CREATE_FILE context_test.py ('Hello Fraiday')")
    print("Turn 2 -> UPDATE_FILE context_test.py ('Hello Fraiday 2')")
    print("Final Output -> Hello Fraiday 2")
    print("Validation -> PASS")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_activity2_portal_verification())
