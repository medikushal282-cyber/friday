import os
import sys
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.workspace.manager import WorkspaceManager
from app.graph.workflow import execute_run_task

os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
ws = WorkspaceManager()

# Ensure hello.py is cleaned up first
hello_path = os.path.join(ws.root_path, "hello.py")
if os.path.exists(hello_path):
    os.remove(hello_path)

run_id = "test_debug"
obj = 'Create a script named hello.py that prints "Hello Fraiday" and execute it.'
runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

asyncio.run(execute_run_task(run_id, obj, runs_db))
print("--- FINAL RESULT ---")
print("STATUS:", runs_db[run_id]["status"])
print("STATE PLAN:", runs_db[run_id]["state"].get("plan"))
print("STATE ERROR:", runs_db[run_id]["state"].get("error"))
print("VALIDATION RESULTS:", runs_db[run_id]["state"].get("validation_results"))
print("OBSERVATIONS:", runs_db[run_id]["state"].get("observations"))
