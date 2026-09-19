import json
import time
import httpx

BASE_URL = "http://localhost:8000"

def test_models_registry():
    print("\n[TEST 1] Testing /api/models Endpoint...")
    res = httpx.get(f"{BASE_URL}/api/models", timeout=10.0)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    models = res.json()
    assert len(models) >= 3, f"Expected at least 3 models, got {len(models)}"
    
    raw_text = res.text
    assert "gsk_" not in raw_text, "CRITICAL: Secret Groq API key leaked in models response!"
    assert "sk-" not in raw_text, "CRITICAL: Secret OpenAI API key leaked in models response!"
    
    model_ids = [m["id"] for m in models]
    print(f"  Found models: {model_ids}")
    assert "qwen/qwen3.8-27b" in model_ids
    assert "llama-3.3-70b-versatile" in model_ids
    
    for m in models:
        assert "id" in m
        assert "provider" in m
        assert "display_name" in m
        assert "capabilities" in m
        assert "status" in m
    print("  [PASS] Models registry verified with strict secret isolation.")

def test_agents_registry():
    print("\n[TEST 2] Testing /api/agents Endpoint...")
    res = httpx.get(f"{BASE_URL}/api/agents", timeout=10.0)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    agents = res.json()
    assert len(agents) == 8, f"Expected 8 specialized agents, got {len(agents)}"
    
    agent_ids = {a["id"]: a for a in agents}
    required_agents = [
        "orchestrator", "researcher", "coding_agent", "testing_agent",
        "debugging_agent", "data_agent", "security_agent", "review_agent"
    ]
    for ra in required_agents:
        assert ra in agent_ids, f"Missing agent: {ra}"
        ag = agent_ids[ra]
        assert "name" in ag
        assert "description" in ag
        assert "capabilities" in ag
        assert "approval_policy" in ag
        print(f"  Verified agent profile: {ra} -> policy={ag['approval_policy']}")
        
    assert agent_ids["security_agent"]["approval_policy"] == "strict"
    assert agent_ids["testing_agent"]["approval_policy"] == "sensitive"
    print("  [PASS] Specialized agents registry verified.")

def test_codex_autonomous_execution_stream():
    print("\n[TEST 3] Testing Autonomous Run with Reasoning Summaries and Artifact Events...")
    payload = {
        "objective": "Create codex_demo.py that prints 'Codex Workspace Active' and runs it to verify output.",
        "mode": "autonomous",
        "model": "qwen/qwen3.8-27b"
    }
    res = httpx.post(f"{BASE_URL}/api/runs/", json=payload, timeout=10.0)
    assert res.status_code == 200, f"Failed to start run: {res.text}"
    run_data = res.json()
    run_id = run_data["run_id"]
    print(f"  Run started: {run_id}")
    
    events_received = []
    reasoning_received = False
    agent_selected_received = False
    artifact_content_received = False
    plan_steps_received = False
    run_completed = False
    
    start_time = time.time()
    with httpx.stream("GET", f"{BASE_URL}/api/runs/{run_id}/events", timeout=60.0) as stream_res:
        assert stream_res.status_code == 200
        for line in stream_res.iter_lines():
            if time.time() - start_time > 60:
                print("  [TIMEOUT] Waiting for run completion timed out.")
                break
            if not line or not line.startswith("data:"):
                continue
            raw_data = line[5:].strip()
            if not raw_data:
                continue
            try:
                data = json.loads(raw_data)
                ev_type = data.get("event")
                events_received.append(ev_type)
                
                if ev_type == "agent_reasoning_summary":
                    reasoning_received = True
                    print(f"  [SSE] Agent reasoning summary: {data.get('data', {}).get('summary')}")
                    
                elif ev_type == "agent_selected":
                    agent_selected_received = True
                    print(f"  [SSE] Agent selected: {data.get('data', {}).get('agent_name')} ({data.get('data', {}).get('role')})")
                    
                elif ev_type == "plan_created":
                    plan_steps_received = True
                    steps = data.get("data", {}).get("steps", [])
                    agent_names = [s.get("agent") for s in steps]
                    print(f"  [SSE] Plan created with {len(steps)} steps: {agent_names}")
                    
                elif ev_type in ("file_created", "file_updated"):
                    if data.get("data", {}).get("content"):
                        artifact_content_received = True
                        print(f"  [SSE] Artifact emitted with content preview: {data.get('data', {}).get('path')}")
                        
                elif ev_type == "run_completed":
                    run_completed = True
                    print("  [SSE] Run completed successfully.")
                    break
                    
                elif ev_type == "run_failed":
                    print(f"  [SSE] Run failed: {data}")
                    break
            except Exception:
                pass
                
    assert reasoning_received, "Expected agent_reasoning_summary event"
    assert agent_selected_received, "Expected agent_selected event"
    assert plan_steps_received, "Expected plan_created event"
    assert artifact_content_received, "Expected artifact content in file_created event"
    assert run_completed, "Expected run_completed event"
    print("  [PASS] Codex execution stream emitted all required architectural events.")

def test_continuation_flow():
    print("\n[TEST 4] Testing Continuation Flow...")
    payload = {
        "objective": "Extend codex_demo.py to also print 'Iteration 2 Complete' and run it.",
        "mode": "autonomous",
        "model": "qwen/qwen3.8-27b"
    }
    res = httpx.post(f"{BASE_URL}/api/runs/", json=payload, timeout=10.0)
    assert res.status_code == 200
    run_id = res.json()["run_id"]
    print(f"  Continuation run started: {run_id}")
    
    completed = False
    start_time = time.time()
    with httpx.stream("GET", f"{BASE_URL}/api/runs/{run_id}/events", timeout=60.0) as stream_res:
        for line in stream_res.iter_lines():
            if time.time() - start_time > 60:
                break
            if not line or not line.startswith("data:"):
                continue
            raw_data = line[5:].strip()
            if not raw_data:
                continue
            try:
                data = json.loads(raw_data)
                if data.get("event") == "run_completed":
                    completed = True
                    break
            except Exception:
                pass
                
    assert completed, "Expected continuation run to complete successfully"
    print("  [PASS] Continuation workflow executed successfully.")

if __name__ == "__main__":
    print("==================================================")
    print("STARTING FRAIDAY CODEX WORKSPACE SCENARIO TESTS")
    print("==================================================")
    test_models_registry()
    test_agents_registry()
    test_codex_autonomous_execution_stream()
    test_continuation_flow()
    print("==================================================")
    print("ALL CODEX WORKSPACE ACCEPTANCE TESTS PASSED!")
    print("==================================================")
