import httpx
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"

def submit_and_stream(objective: str):
    print(f"\n>>> SUBMITTING OBJECTIVE: {objective}")
    resp = httpx.post(f"{BASE_URL}/api/runs/", json={"objective": objective}, timeout=10.0)
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"Run ID: {run_id}")

    events_received = []
    with httpx.stream("GET", f"{BASE_URL}/api/runs/{run_id}/events", timeout=60.0) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                events_received.append(event)
                evt_type = event["event"]
                node = event.get("node", "")
                data = event.get("data", {})
                
                if evt_type in ["tool_call_started", "tool_call_completed"]:
                    print(f"  [{evt_type.upper()}] tool={data.get('tool')} path={data.get('path', '')}")
                elif evt_type in ["file_created", "file_updated", "file_deleted", "file_read"]:
                    print(f"  [{evt_type.upper()}] path={data.get('path')} status={data.get('status', 'ok')}")
                elif evt_type in ["command_started", "command_completed"]:
                    print(f"  [{evt_type.upper()}] cmd={data.get('command')} exit={data.get('exit_code', '-')}")
                elif evt_type == "validation_result":
                    print(f"  [VALIDATION] valid={data.get('valid')} reason={data.get('reason')}")
                elif evt_type in ["run_completed", "run_failed", "approval_required"]:
                    print(f"  [STREAM_END] {evt_type}")
                    break

    state_resp = httpx.get(f"{BASE_URL}/api/runs/{run_id}", timeout=10.0)
    state_resp.raise_for_status()
    state = state_resp.json()["state"]
    return state, events_received

def run_phase4_6_demos():
    print("==================================================")
    print("PHASE 4.6 — ACTION-ORIENTED AGENT ACCEPTANCE DEMOS")
    print("==================================================")

    # Ensure clean starting state: factorial.py does not exist
    from app.workspace.manager import get_workspace_manager
    ws = get_workspace_manager()
    try:
        ws.delete_file("factorial.py")
    except Exception:
        pass
    assert not os.path.exists(os.path.join(ws.root_path, "factorial.py")), "factorial.py should not exist at start"

    # DEMO 1: Step 16 - Real CRUD Acceptance Demo (Create & Execute)
    print("\n--- DEMO 1: Step 16 - Create Factorial Program ---")
    obj1 = "Create a recursive Python factorial program for 5, save it as factorial.py, run it, and verify the result."
    state1, evts1 = submit_and_stream(obj1)
    
    # Assertions for Demo 1
    obs1 = state1.get("observations", [])
    assert obs1, "No observations recorded!"
    run_obs1 = next((o for o in obs1 if o.get("tool") == "run_command" or "stdout" in o), obs1[-1])
    stdout1 = run_obs1.get("stdout", "").strip()
    assert run_obs1.get("exit_code") == 0, f"Expected exit code 0, got {run_obs1.get('exit_code')}"
    assert "120" in stdout1, f"Expected 120 in stdout, got {stdout1}"
    assert state1.get("validation_results", [{}])[-1].get("valid") is True, "Validation should pass"
    assert any(a.get("path") == "factorial.py" and a.get("operation") == "created" for a in state1.get("artifacts", [])), "Artifact not tracked"
    print("  -> DEMO 1 PASSED: factorial.py created, executed, output: 120, validated PASS.")

    # DEMO 2: Step 17 - Update Acceptance Demo (Follow-up turn)
    print("\n--- DEMO 2: Step 17 - Update Existing Program ---")
    obj2 = "Modify factorial.py so it also prints factorial(6), then run it."
    state2, evts2 = submit_and_stream(obj2)
    
    # Assertions for Demo 2
    obs2 = state2.get("observations", [])
    assert obs2, "No observations recorded in update turn!"
    exec_obs2 = next((o for o in obs2 if "command" in o or o.get("tool") == "run_command"), obs2[-1])
    stdout2 = exec_obs2.get("stdout", "").strip()
    assert exec_obs2.get("exit_code") == 0, f"Expected exit code 0, got {exec_obs2.get('exit_code')}"
    assert "120" in stdout2, f"Expected 120 in stdout, got {stdout2}"
    assert "720" in stdout2, f"Expected 720 in stdout, got {stdout2}"
    assert any(e.get("event") == "file_updated" for e in evts2), "Expected file_updated event"
    print("  -> DEMO 2 PASSED: factorial.py updated using context, executed, output: 120 and 720.")

    # DEMO 3: Step 18 - Read Acceptance Demo
    print("\n--- DEMO 3: Step 18 - Read File Content ---")
    obj3 = "Show me what is currently inside factorial.py."
    state3, evts3 = submit_and_stream(obj3)
    
    # Assertions for Demo 3
    obs3 = state3.get("observations", [])
    assert obs3, "No read observation recorded!"
    read_obs = next((o for o in obs3 if o.get("tool") == "read_file" or "stdout" in o), obs3[0])
    stdout3 = read_obs.get("stdout", "").strip()
    assert read_obs.get("exit_code") == 0
    assert "def factorial" in stdout3, f"Expected Python source code, got: {stdout3}"
    assert any(e.get("event") == "file_read" for e in evts3), "Expected file_read event"
    print("  -> DEMO 3 PASSED: Read factorial.py content directly without regenerating.")

    # DEMO 4: Step 19 - Delete Safety Policy Demo
    print("\n--- DEMO 4: Step 19 - Delete File with Approval Required ---")
    obj4 = "Delete factorial.py."
    state4, evts4 = submit_and_stream(obj4)
    
    # Assertions for Demo 4
    assert state4.get("approval_required") is True, "Expected approval_required flag to be True"
    obs4 = state4.get("observations", [])
    assert any(o.get("status") == "approval_required" for o in obs4), "Expected approval_required status in observation"
    # Verify file still exists on disk because deletion was paused for approval
    assert os.path.exists(os.path.join(ws.root_path, "factorial.py")), "File should NOT have been deleted automatically!"
    print("  -> DEMO 4 PASSED: Delete action intercepted by policy; approval_required returned; file preserved on disk.")

    print("\n==================================================")
    print("ALL 4 CRUD DEMOS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_phase4_6_demos()
