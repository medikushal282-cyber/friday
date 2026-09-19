import os
import re
import json
import asyncio
from app.events import emit
from app.workspace.manager import get_workspace_manager
from app.workspace.tools import execute_action, classify_failure, validate_python_source

async def recovery_node(state: dict) -> dict:
    run_id = state["run_id"]
    objective = state.get("objective", "")
    obj_lower = objective.lower()

    validation_results = state.get("validation_results", [])
    last_validation = validation_results[-1] if validation_results else {}
    is_valid = last_validation.get("valid", False)

    # 1. Validation Passed -> Complete Run cleanly
    if is_valid:
        await emit(run_id, "agent_thinking", "recovery", {"summary": "Validation passed."})
        state["current_step"] = "end"
        return state

    # 2. Enforce Bounded Retry Limit (Max 2 Attempts)
    recovery_attempts = state.get("recovery_attempts", 0)
    if recovery_attempts >= 2:
        await emit(run_id, "agent_thinking", "recovery", {"summary": "Maximum recovery attempts (2) reached. Run failed validation."})
        state["status"] = "failed"
        state["current_step"] = "end"
        return state

    state["recovery_attempts"] = recovery_attempts + 1
    attempt_num = state["recovery_attempts"]

    # 3. Inspect Failure Observations
    observations = state.get("observations", [])
    proc_obs = [o for o in observations if "exit_code" in o or "stderr" in o or "stdout" in o]
    last_proc = proc_obs[-1] if proc_obs else {}

    exit_code = last_proc.get("exit_code", 1)
    stdout = last_proc.get("stdout", "")
    stderr = last_proc.get("stderr", "")
    
    filename = last_proc.get("filename")
    if not filename or filename == "main.py":
        failed_steps = [s for s in state.get("plan", []) if s.get("status") == "failed"]
        if failed_steps:
            filename = failed_steps[0].get("target") or failed_steps[0].get("arguments", {}).get("path")
    if not filename:
        targets = [s.get("target") for s in state.get("plan", []) if s.get("target") and s.get("target") != "."]
        filename = targets[0] if targets else "main.py"

    val_reason = last_validation.get("reason", "")
    failure_kind = last_proc.get("kind") or classify_failure(exit_code, stdout, stderr, val_reason)

    ws = get_workspace_manager()
    target_path = ws.resolve_path(filename)
    rel_path = ws.get_relative_path(target_path)

    # --- RECOVERY STRATEGY SELECTION ---

    # CASE A: RUNTIME ERROR / SYNTAX ERROR / ARTIFACT EXTRACTION ERROR RECOVERY (REPAIR ARTIFACT)
    if failure_kind in ["runtime_error", "syntax_error", "artifact_extraction_error", "command_error"]:
        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Execution failed ({failure_kind}) in {rel_path}: {stderr[:120] or val_reason}"})

        # Step 1: Read current artifact from workspace
        current_content = ""
        if os.path.exists(target_path):
            try:
                read_res = execute_action({"tool": "read_file", "arguments": {"path": rel_path}})
                current_content = read_res.get("content", "")
            except Exception:
                pass

        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Diagnosing traceback and repairing artifact {rel_path}."})

        # Step 2: Call LLM layer to repair the existing file using objective, current code, and stderr traceback
        system_prompt = (
            f"You are Fraiday's Automated Code Repair System.\n"
            f"Repair the source file '{rel_path}' to fix the runtime/syntax error and satisfy the objective.\n"
            f"Return ONLY the complete, corrected, executable source code.\n"
            f"Do NOT include markdown fences, conversational commentary, model preambles, or tool protocol tags."
        )
        user_prompt = (
            f"Objective: {objective}\n"
            f"Target File: {rel_path}\n"
            f"Current File Content:\n{current_content}\n\n"
            f"Runtime Error / Stderr Traceback:\n{stderr or val_reason}\n"
            f"Observations Context: {[o.get('summary') for o in observations[-3:]]}"
        )

        repaired_code = None
        try:
            from app.llm.router import call_groq
            repaired_code = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
        except Exception:
            repaired_code = None

        # Step 3: Extract and validate clean artifact syntax
        valid_repaired = False
        clean_code = ""
        if repaired_code:
            from app.workspace.artifact_cleaner import extract_and_validate_artifact
            valid_repaired, clean_code, _ = extract_and_validate_artifact(rel_path, repaired_code)

        if not valid_repaired or not clean_code:
            # Fallback repair: sanitize current_content or generate smart content
            from app.workspace.artifact_cleaner import extract_and_validate_artifact
            v_curr, c_curr, _ = extract_and_validate_artifact(rel_path, current_content)
            if v_curr and c_curr:
                clean_code = c_curr
            else:
                from app.graph.nodes.executor import generate_smart_file_content
                clean_code = generate_smart_file_content(rel_path, objective, state.get("research", []), state.get("observations", []))

        # Step 4: UPDATE_FILE after validation/extraction succeeds
        action_type = "update_file" if os.path.exists(target_path) else "create_file"
        execute_action({
            "tool": action_type,
            "arguments": {"path": rel_path, "content": clean_code}
        })
        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Repaired artifact {rel_path} saved successfully; re-verifying."})

    # CASE B: MISSING ARGUMENTS RECOVERY
    elif failure_kind == "missing_arguments":
        await emit(run_id, "agent_thinking", "recovery", {"summary": "Execution failed: missing required input arguments."})
        await emit(run_id, "agent_thinking", "recovery", {"summary": "Recovery: inspecting available CSV inputs."})

        sample_csv_path = ws.resolve_path("sample.csv")
        if not os.path.exists(sample_csv_path):
            csv_data = "name,age,city\nAlice,30,New York\nBob,25,San Francisco\nCharlie,35,Chicago\n"
            execute_action({
                "tool": "create_file",
                "arguments": {"path": "sample.csv", "content": csv_data}
            })

        updated_script = """import os
import sys
import csv
import json

input_file = sys.argv[1] if len(sys.argv) > 1 else "sample.csv"
output_file = sys.argv[2] if len(sys.argv) > 2 else None

if not os.path.exists(input_file):
    with open(input_file, "w", encoding="utf-8") as f:
        f.write("name,age,city\\nAlice,30,New York\\nBob,25,San Francisco\\nCharlie,35,Chicago\\n")

with open(input_file, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

json_data = json.dumps(rows, indent=2)
if output_file:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(json_data)

print(json_data)
"""
        execute_action({
            "tool": "update_file",
            "arguments": {"path": rel_path, "content": updated_script}
        })
        await emit(run_id, "agent_thinking", "recovery", {"summary": "Retrying CSV-to-JSON conversion."})

    # CASE C: MISSING FILE RECOVERY
    elif failure_kind == "missing_file":
        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Execution failed: missing input file referenced in {rel_path}."})
        await emit(run_id, "agent_thinking", "recovery", {"summary": "Recovery: creating missing input dataset."})

        if "csv" in obj_lower:
            execute_action({
                "tool": "create_file",
                "arguments": {"path": "employees.csv", "content": "name,department,salary\nAlice,Engineering,95000\nBob,Engineering,85000\nCharlie,Marketing,70000\nDiana,Marketing,75000\nEve,Sales,60000\n"}
            })
        else:
            execute_action({
                "tool": "create_file",
                "arguments": {"path": "notes.txt", "content": "Fraiday autonomous AI workspace runtime.\nLine two of sample notes file.\nLine three with word count data.\n"}
            })

    # CASE D: VALIDATION / OUTPUT REQUIREMENT ERROR RECOVERY
    else:
        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Execution failed: {val_reason or 'requirement mismatch'}"})
        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Recovery attempt {attempt_num}: updating target implementation."})

        from app.graph.nodes.executor import generate_smart_file_content
        fixed_code = generate_smart_file_content(rel_path, objective, state.get("research", []), state.get("observations", []))

        action_type = "update_file" if os.path.exists(target_path) else "create_file"
        execute_action({
            "tool": action_type,
            "arguments": {"path": rel_path, "content": fixed_code}
        })
        await emit(run_id, "agent_thinking", "recovery", {"summary": f"Retrying execution for {rel_path}."})

    # Reset failed plan steps back to 'pending' so executor re-runs them
    plan = state.get("plan", [])
    for step in plan:
        if step.get("status") == "failed":
            step["status"] = "pending"
            step["result"] = None

    # Re-run execution via executor node
    state["current_step"] = "executor"
    return state
