import httpx
import json
import sys

def test():
    objective = "Write a python script that prints the numbers 1 to 10, one per line."
    
    print(f"Submitting POST /api/runs with objective: {objective}")
    resp = httpx.post("http://127.0.0.1:8000/api/runs/", json={"objective": objective})
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"Started run_id: {run_id}")
    
    print("Listening to SSE stream...")
    with httpx.stream("GET", f"http://127.0.0.1:8000/api/runs/{run_id}/events", timeout=120.0) as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                event = data["event"]
                node = data.get("node", "")
                print(f"EVENT: {event.ljust(15)} | NODE: {node.ljust(12)} | TS: {data['ts']}")
                if event == "run_completed" or event == "run_failed":
                    print("Stream ended.")
                    break
                    
    print("\nFetching final state...")
    state_resp = httpx.get(f"http://127.0.0.1:8000/api/runs/{run_id}")
    state_resp.raise_for_status()
    state_data = state_resp.json()["state"]
    
    obs = state_data.get("observations", [])
    val_results = state_data.get("validation_results", [])
    
    exec_obs = obs[0] if obs else {}
    
    print("\n--- FINAL STATE SUMMARY ---")
    print("Observations:")
    print(json.dumps(obs, indent=2))
    print("Validation Results:")
    print(json.dumps(val_results, indent=2))
    
    print("\n--- EXECUTION DETAILS ---")
    print(f"Stdout:\n{exec_obs.get('stdout', '')}")
    print(f"Stderr:\n{exec_obs.get('stderr', '')}")
    print(f"Exit Code: {exec_obs.get('exit_code')}")

if __name__ == "__main__":
    test()
