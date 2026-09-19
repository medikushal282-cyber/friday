import os
import sys
import asyncio
import json
import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import get_workspace_manager
from app.graph.workflow import execute_run_task

async def run_portal_test():
    print("==================================================")
    print("RUNNING FRAIDAY PORTAL TOOL & ACTION VERIFICATION")
    print("==================================================")

    ws = get_workspace_manager()
    # Clean up any pre-existing tool_test.py
    try:
        ws.delete_file("tool_test.py")
    except Exception:
        pass

    run_id = "test_run_portal_001"
    objective = "Create a file named tool_test.py that prints the numbers 1 through 5. Run it and verify that the output is correct."
    runs_db = {
        run_id: {
            "run_id": run_id,
            "objective": objective,
            "status": "pending",
            "state": {}
        }
    }

    print(f"Submitting Objective: {objective}")
    
    # Execute workflow task directly
    await execute_run_task(run_id, objective, runs_db)

    state = runs_db[run_id]["state"]
    status = runs_db[run_id]["status"]
    
    print("\n--- RUN EXECUTED ---")
    print("Run Status:", status)
    print("Run Error:", runs_db[run_id]["state"].get("error"))
    print("Tool Calls:", json.dumps(state.get("tool_calls", []), indent=2))
    print("Observations:", json.dumps(state.get("observations", []), indent=2))
    print("Validation Results:", json.dumps(state.get("validation_results", []), indent=2))
    print("Artifacts:", json.dumps(state.get("artifacts", []), indent=2))

    # Assertions
    assert status == "completed", f"Expected completed, got {status}"
    
    # Check created file on disk
    abs_tool_test = os.path.join(ws.root_path, "tool_test.py")
    assert os.path.exists(abs_tool_test), "tool_test.py should exist on disk"
    
    with open(abs_tool_test, "r", encoding="utf-8") as f:
        file_content = f.read()
    print("\ntool_test.py Content:\n", file_content)

    obs = state.get("observations", [])
    assert obs, "Expected at least one observation"
    proc_obs = next((o for o in reversed(obs) if "exit_code" in o), obs[-1])
    
    stdout = proc_obs.get("stdout", "").strip()
    exit_code = proc_obs.get("exit_code")

    print("\nExecution Output:")
    print("Exit Code:", exit_code)
    print("stdout:", stdout)

    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
    assert "1" in stdout and "5" in stdout, f"Expected numbers 1..5 in stdout, got {stdout}"

    val_res = state.get("validation_results", [{}])[-1]
    assert val_res.get("valid") is True, f"Validation failed: {val_res}"

    print("\n==================================================")
    print("PORTAL VERIFICATION TEST PASSED SUCCESSFULLY!")
    print("CREATE_FILE -> success")
    print("RUN_COMMAND -> success")
    print(f"stdout ->\n{stdout}")
    print("validation -> PASS")
    print("==================================================")

if __name__ == "__main__":
    asyncio.run(run_portal_test())
