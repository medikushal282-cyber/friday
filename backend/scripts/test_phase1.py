import httpx
import json

def test():
    print("Submitting POST /api/runs...")
    resp = httpx.post("http://127.0.0.1:8000/api/runs/", json={"objective": "Test phase 1"})
    resp.raise_for_status()
    run_id = resp.json()["run_id"]
    print(f"Started run_id: {run_id}")
    
    print("Listening to SSE stream...")
    with httpx.stream("GET", f"http://127.0.0.1:8000/api/runs/{run_id}/events") as r:
        for line in r.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                print(f"EVENT: {data['event'].ljust(15)} | NODE: {data.get('node', '').ljust(12)} | TS: {data['ts']}")
                if data["event"] == "run_completed":
                    print("Stream ended correctly.")
                    break

if __name__ == "__main__":
    test()
