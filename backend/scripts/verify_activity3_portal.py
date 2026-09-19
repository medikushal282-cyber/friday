import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import get_workspace_manager
from app.graph.workflow import execute_run_task

async def run_activity3_portal_verification():
    print("==================================================")
    print("ACTIVITY 3 — AUTONOMOUS RESEARCHER PORTAL TEST")
    print("==================================================")

    ws = get_workspace_manager()
    for fname in ["csv_to_json.py", "data.csv"]:
        try:
            ws.delete_file(fname)
        except Exception:
            pass

    # TEST A: External Knowledge Objective
    run_id1 = "act3_run_001"
    obj1 = "Create a Python script that converts a CSV file to JSON using Python's standard library. Research the correct CSV-to-JSON approach first, then create and run the script."
    runs_db = {run_id1: {"run_id": run_id1, "objective": obj1, "status": "pending", "state": {}}}

    print(f"\n--- TEST A (RESEARCH REQUIRED): {obj1} ---")
    await execute_run_task(run_id1, obj1, runs_db)

    state1 = runs_db[run_id1]["state"]
    status1 = runs_db[run_id1]["status"]
    print("Status:", status1)
    assert status1 == "completed"

    research1 = state1.get("research", [])
    print("\nStructured Research Findings:")
    print(json.dumps(research1, indent=2))

    assert len(research1) > 0 and research1[0].get("status") == "accepted", "Research finding should be accepted"
    finding1 = research1[0]
    assert "query" in finding1 and "finding" in finding1 and "source" in finding1 and "relevance" in finding1

    obs1 = next(o for o in reversed(state1.get("observations", [])) if "exit_code" in o)
    stdout1 = obs1.get("stdout", "").strip()
    print("\nExecution Output:\n", stdout1)
    assert obs1.get("exit_code") == 0
    assert "Alice" in stdout1 or "name" in stdout1

    val_res1 = state1.get("validation_results", [{}])[-1]
    assert val_res1.get("valid") is True, f"Validation failed: {val_res1}"

    # TEST B: No Research Required Objective
    run_id2 = "act3_run_002"
    obj2 = "Create a Python script that prints Hello Fraiday."
    runs_db[run_id2] = {"run_id": run_id2, "objective": obj2, "status": "pending", "state": {}}

    print(f"\n--- TEST B (NO UNNECESSARY RESEARCH): {obj2} ---")
    await execute_run_task(run_id2, obj2, runs_db)

    state2 = runs_db[run_id2]["state"]
    status2 = runs_db[run_id2]["status"]
    print("Status:", status2)
    assert status2 == "completed"

    research2 = state2.get("research", [])
    print("Research array:", research2)
    assert len(research2) > 0 and research2[0].get("needed") is False, "Should detect no knowledge gap for simple task"

    print("\n==================================================")
    print("ACTIVITY 3 PORTAL VERIFICATION PASSED SUCCESSFULLY!")
    print("Test A -> Knowledge Gap Detected -> Research Finding Accepted -> Code Created & Executed -> PASS")
    print("Test B -> No Knowledge Gap Detected -> Unnecessary Research Skipped -> PASS")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_activity3_portal_verification())
