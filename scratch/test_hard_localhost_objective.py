import os
import sys
import asyncio
import json

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from app.workspace.manager import WorkspaceManager
from app.graph.workflow import execute_run_task

os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
ws = WorkspaceManager()

# Create existing employees.csv to test workspace discovery & plan obsolescence / re-planning
sample_csv_path = os.path.join(ws.root_path, "sample_csv.csv")
with open(sample_csv_path, "w", encoding="utf-8") as f:
    f.write("name,department,salary\nAlice,Engineering,95000\nBob,Engineering,85000\nCharlie,Marketing,70000\nDiana,Marketing,75000\nEve,Sales,60000\n")

run_id = "test_hard_req13"
obj = """Build a small employee reporting project in the workspace.

First inspect the workspace and reuse any suitable existing CSV input instead of creating duplicate data.

Create or update an employee CSV if genuinely required.

Create employee_report.py using Python's standard library.

The script must:
- read employee CSV data
- group employees by department
- calculate average salary per department
- write department_report.json

Run the script.

If execution fails, inspect the actual error and recover autonomously.

If the existing input or generated files make the original plan unnecessary, re-plan instead of repeating those steps.

Read department_report.json.

Validate that:
- it is valid JSON
- each department has an average salary
- the report contains data derived from the CSV

Create README_employee_report.md explaining how to use the project.

Finish only after final validation succeeds."""

runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

asyncio.run(execute_run_task(run_id, obj, runs_db))
state = runs_db[run_id]["state"]

print("=== HARD LOCALHOST TEST RESULT ===")
print("STATUS:", runs_db[run_id]["status"])
print("REPLANS COUNT:", state.get("replan_count"))
print("AUTONOMOUS ITERATIONS:", state.get("autonomous_iteration_count"))
print("VALIDATION RESULTS:", state.get("validation_results"))
print("OBSERVATIONS LIST:")
for obs in state.get("observations", []):
    print("  OBS:", obs)
