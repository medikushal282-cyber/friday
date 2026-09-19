with open('backend/app/graph/workflow.py', 'r') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'while state["current_step"] != "end":' in line and i < 150:
        lines.insert(i+1, '            if state.get("is_cancelled"):\n                runs_db[run_id]["status"] = "cancelled"\n                break\n')
        break
with open('backend/app/graph/workflow.py', 'w') as f:
    f.writelines(lines)
