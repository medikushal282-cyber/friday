import os
import sys

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.workspace.process_manager import (
    classify_command, get_process_registry, COMMAND_NORMAL, COMMAND_LONG_RUNNING, COMMAND_WEB_PREVIEW
)
from app.workspace.tools import tool_run_command, tool_start_server, tool_stop_server, execute_action
from app.graph.nodes.validator import validator_node

def test_1_synchronous_command_execution(tmp_path):
    """TEST 1: Normal synchronous command (python script.py) completes with exit code 0 and captures stdout."""
    script_file = tmp_path / "hello_sync.py"
    script_file.write_text("print('HELLO_SYNC_STDOUT')\n", encoding="utf-8")

    res = tool_run_command(f"{sys.executable} {script_file}")
    assert res["success"] is True
    assert res["exit_code"] == 0
    assert "HELLO_SYNC_STDOUT" in res["stdout"]

def test_2_web_server_command_auto_classification(tmp_path):
    """TEST 2: Server command (python -m http.server 5590) auto-classifies as server and returns server_started non-blockingly."""
    cmd = "python -m http.server 5590"
    kind = classify_command(cmd)
    assert kind == COMMAND_WEB_PREVIEW

    # Tool run_command must auto-route to non-blocking server start
    res = tool_run_command(cmd)
    assert res["success"] is True
    assert res["exit_code"] == 0
    assert res.get("status") == "server_started" or res.get("result", {}).get("status") == "server_started"

    # Stop server after test
    tool_stop_server(port=5590)

def test_3_html_preview_start_server(tmp_path):
    """TEST 3: START_SERVER action on ecommerce.html starts web preview and returns valid URL."""
    html_file = tmp_path / "ecommerce.html"
    html_file.write_text("<!DOCTYPE html><html><body><h1>KICKLAB</h1></body></html>", encoding="utf-8")

    res = tool_start_server(target="ecommerce.html", port=5591)
    assert res["success"] is True
    assert "http://localhost:5591" in res["url"]

    # Stop server after test
    tool_stop_server(port=5591)

def test_4_stop_server(tmp_path):
    """TEST 4: STOP_SERVER action terminates managed server process."""
    res_start = tool_start_server(target="index.html", port=5592)
    assert res_start["success"] is True

    res_stop = tool_stop_server(port=5592)
    assert res_stop["success"] is True

def test_5_repeated_preview_server_reuse(tmp_path):
    """TEST 5: Repeated preview start request for same workspace reuses existing active server safely."""
    res1 = tool_start_server(target="index.html", port=5593)
    assert res1["success"] is True

    res2 = tool_start_server(target="index.html", port=5593)
    assert res2["success"] is True
    assert res2.get("result", {}).get("reused") is True or res2.get("reused") is True

    tool_stop_server(port=5593)

def test_6_bounded_startup_failure_test():
    """TEST 6: Invalid process command fails within bounded startup check without hanging."""
    reg = get_process_registry()
    res = reg.start_long_running_process(
        command=[sys.executable, "-c", "import sys; print('CRASH_ERR', file=sys.stderr); sys.exit(42)"],
        cwd=os.getcwd(),
        timeout=3.0
    )
    assert res["success"] is False
    assert res["status"] == "failed"
    assert res["exit_code"] == 42
    assert "CRASH_ERR" in res["error"]

def test_7_sse_lifecycle_and_server_persistence():
    """TEST 7: python -m http.server 5500 -> preview_started -> run_completed -> SSE closes cleanly -> Server remains alive."""
    import asyncio
    from app.events import emit, get_queue
    from app.api.runs import RUNS_DB

    run_id = "test_run_sse_lifecycle"
    RUNS_DB[run_id] = {"run_id": run_id, "status": "pending", "state": {}}

    # 1. Start web preview server
    res = tool_start_server(target="ecommerce.html", port=5594, run_id=run_id)
    assert res["success"] is True

    # 2. Emit lifecycle events into SSE queue
    asyncio.run(emit(run_id, "preview_started", "executor", {"url": res["url"], "port": 5594}))
    asyncio.run(emit(run_id, "run_completed", "recovery", {"status": "completed"}))

    # 3. Consume SSE events queue until run_completed
    q = get_queue(run_id)
    received_events = []
    while not q.empty():
        evt = asyncio.run(q.get())
        received_events.append(evt["event"])

    assert "preview_started" in received_events
    assert "run_completed" in received_events

    # 4. Verify web preview server process remains alive in ManagedProcessRegistry after SSE stream completion
    reg = get_process_registry()
    proc = reg.get_process("5594") or reg.get_process("proc_web_5594")
    assert proc is not None
    assert proc["status"] == "RUNNING"

    # Cleanup
    tool_stop_server(port=5594)

