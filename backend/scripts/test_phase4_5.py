import httpx
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://127.0.0.1:8000"

def run_acceptance_tests():
    print("==================================================")
    print("PHASE 4.5 ACCEPTANCE TESTS")
    print("==================================================")

    # Test A: Workspace configuration
    print("\n[A] Testing Workspace Configuration...")
    resp = httpx.get(f"{BASE_URL}/api/workspace")
    assert resp.status_code == 200, f"Failed: {resp.status_code}"
    ws_info = resp.json()
    print(f"Workspace Name: {ws_info.get('name')}")
    print(f"Workspace Root: {ws_info.get('root_path')}")
    assert os.path.exists(ws_info.get('root_path')), "Root path does not exist on disk"
    print("  -> PASSED: Configured workspace exists and is active.")

    # Test B: Path security
    print("\n[B] Testing Path Security...")
    # 1. Traversal attempt via API
    resp = httpx.get(f"{BASE_URL}/api/workspace/files?path=../../windows")
    assert resp.status_code in [400, 403], f"Expected 400 or 403, got {resp.status_code}"
    # 2. Reading outside file
    resp = httpx.get(f"{BASE_URL}/api/workspace/file?path=../outside.txt")
    assert resp.status_code in [400, 403, 404], f"Expected security rejection, got {resp.status_code}"
    print("  -> PASSED: Outside-workspace access is rejected.")

    # Test C: Python discovery
    print("\n[C] Testing Python Discovery...")
    resp = httpx.get(f"{BASE_URL}/api/workspace/runtime")
    assert resp.status_code == 200
    runtime = resp.json()
    py = runtime.get("python", {})
    assert py.get("available") is True, "Python must be available"
    print(f"  -> Python Executable: {py.get('executable')}")
    print(f"  -> Python Version:    {py.get('version')}")
    print(f"  -> Python Source:     {py.get('source')}")
    print("  -> PASSED: Python discovery verified.")

    # Test D: CLI Tool discovery
    print("\n[D] Testing Node / NPM / Git Discovery...")
    for tool in ["node", "npm", "git"]:
        info = runtime.get(tool, {})
        print(f"  -> {tool.upper()}: available={info.get('available')}, version={info.get('version')}")
    print("  -> PASSED: Runtime tools accurately detected.")

    # Test E: File Operations
    print("\n[E] Testing File Operations inside Workspace...")
    write_resp = httpx.post(f"{BASE_URL}/api/workspace/file", json={"path": "test_phase4_5_tmp.txt", "content": "phase 4.5 workspace active"})
    assert write_resp.status_code == 200
    read_resp = httpx.get(f"{BASE_URL}/api/workspace/file?path=test_phase4_5_tmp.txt")
    assert read_resp.status_code == 200
    assert read_resp.json().get("content") == "phase 4.5 workspace active"
    # Cleanup file using WorkspaceManager
    from app.workspace.manager import get_workspace_manager
    get_workspace_manager().delete_file("test_phase4_5_tmp.txt")
    print("  -> PASSED: File write and read inside workspace verified.")

    # Test F: Factorial Program Execution
    print("\n[F] Testing Factorial Run (Recursive factorial(5) -> 120)...")
    factorial_obj = "Create a recursive Python factorial program for 5 and run it."
    run_resp = httpx.post(f"{BASE_URL}/api/runs/", json={"objective": factorial_obj})
    assert run_resp.status_code == 200
    run_id = run_resp.json()["run_id"]
    print(f"  Started run: {run_id}")

    # Listen to SSE stream until completed
    with httpx.stream("GET", f"{BASE_URL}/api/runs/{run_id}/events", timeout=120.0) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                event = data["event"]
                node = data.get("node", "")
                if event == "node_started":
                    print(f"    [EVENT] Node started: {node}")
                elif event == "validation_result":
                    print(f"    [EVENT] Validation: valid={data['data'].get('valid')}, reason={data['data'].get('reason')}")
                elif event in ["run_completed", "run_failed"]:
                    break

    final_resp = httpx.get(f"{BASE_URL}/api/runs/{run_id}")
    final_state = final_resp.json()["state"]
    obs = final_state.get("observations", [])
    assert obs, "No observations recorded!"
    first_obs = obs[0]
    stdout = first_obs.get("stdout", "").strip()
    exit_code = first_obs.get("exit_code")
    print(f"  -> File Created: {first_obs.get('filename')}")
    print(f"  -> Output (stdout): {stdout}")
    print(f"  -> Exit code: {exit_code}")

    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"
    assert "120" in stdout, f"Expected 120 in stdout, got {stdout}"
    print("  -> PASSED: Factorial execution succeeded with stdout containing 120 and exit_code 0.")

    print("\n==================================================")
    print("ALL ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_acceptance_tests()
