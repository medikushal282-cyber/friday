import os
import re
import json
import asyncio
from typing import List, Dict, Any, Optional

from app.events import emit
from app.llm.router import call_groq
from app.workspace.manager import get_workspace_manager
from app.workspace.tools import execute_tool

def determine_target_filename(objective: str, context: List[dict] = None) -> str:
    m = re.search(r'\b([a-zA-Z0-9_\-]+\.py)\b', objective, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    
    obj_lower = objective.lower()
    if "factorial" in obj_lower:
        return "factorial.py"
        
    if "fibonacci" in obj_lower:
        return "fibonacci.py"

    if re.search(r'\b(it|this|that|the file)\b', obj_lower):
        # Check if a file was referenced in context
        if context:
            for turn in reversed(context):
                for art in turn.get("artifacts", []):
                    p = art.get("path")
                    if p and p.endswith(".py"):
                        return p
        return "factorial.py"
        
    if context:
        for turn in reversed(context):
            for art in turn.get("artifacts", []):
                p = art.get("path")
                if p and p.endswith(".py"):
                    return p
                    
    return "main.py"

def clean_python_code(code: str) -> str:
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
    code = code.strip()
    if code.startswith("python\n"):
        code = code[7:]
    return code.strip()

async def executor_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "executor", {"summary": "Executing action plan through controlled workspace tools."})
    
    run_id = state["run_id"]
    objective = state["objective"]
    obj_lower = objective.lower()
    ws = get_workspace_manager()
    python_exe = ws.get_python_executable()
    target_file = determine_target_filename(objective, state.get("conversation_context"))
    
    # Track steps in plan assigned to executor
    executor_steps = [s for s in state.get("plan", []) if s.get("agent") == "executor"]
    current_step_idx = 0

    def get_next_step():
        nonlocal current_step_idx
        if current_step_idx < len(executor_steps):
            step = executor_steps[current_step_idx]
            current_step_idx += 1
            return step
        return None

    # SCENARIO 1: DELETE OPERATION (Delete safety demo)
    if "delete" in obj_lower or "remove" in obj_lower:
        step = get_next_step()
        if step:
            step["status"] = "running"
            await emit(run_id, "step_started", "executor", {"step_id": step["id"]})

        await emit(
            run_id,
            "tool_call_started",
            "executor",
            {
                "tool": "delete_file",
                "path": target_file
            }
        )

        del_res = await asyncio.to_thread(
            execute_tool,
            "delete_file",
            path=target_file
        )

        await emit(
            run_id,
            "tool_call_completed",
            "executor",
            del_res
        )

        if del_res.get("status") == "approval_required":
            # Pause execution and request explicit human approval.
            state["approval_required"] = True
            state["approval_status"] = "pending"
            state["approval_request"] = {
                "tool": "delete_file",
                "path": target_file,
                "reason": del_res.get(
                    "reason",
                    "Destructive file deletion requires explicit user approval."
                )
            }

            obs = {
                "tool": "delete_file",
                "path": target_file,
                "status": "approval_required",
                "message": del_res.get("reason"),
                "exit_code": 0
            }

            # Do NOT claim the file was deleted.
            await emit(
                run_id,
                "approval_requested",
                "executor",
                state["approval_request"]
            )

        else:
            obs = {
                "tool": "delete_file",
                "path": target_file,
                "status": "deleted" if del_res.get("success") else "failed",
                "exit_code": 0 if del_res.get("success") else 1
            }

            if del_res.get("success"):
                await emit(
                    run_id,
                    "file_deleted",
                    "executor",
                    {
                        "path": target_file,
                        "status": "deleted"
                    }
                )

        state.setdefault("observations", []).append(obs)
        if step:
            step["status"] = "completed"
            await emit(run_id, "step_completed", "executor", {"step_id": step["id"], "status": "completed"})

        if state.get("approval_status") == "pending":
            state["status"] = "paused"
            return state

        state["current_step"] = "validator"
        return state

    # SCENARIO 2: READ OPERATION (Read acceptance demo)
    if ("show" in obj_lower or "read" in obj_lower or "inside" in obj_lower or "view" in obj_lower) and not ("create" in obj_lower or "modify" in obj_lower):
        step = get_next_step()
        if step:
            step["status"] = "running"
            await emit(run_id, "step_started", "executor", {"step_id": step["id"]})

        await emit(run_id, "tool_call_started", "executor", {"tool": "read_file", "path": target_file})
        read_res = await asyncio.to_thread(execute_tool, "read_file", path=target_file)
        await emit(run_id, "tool_call_completed", "executor", read_res)
        await emit(run_id, "file_read", "executor", {"path": target_file, "success": read_res.get("success")})

        content = read_res.get("content", "")
        obs = {
            "tool": "read_file",
            "filename": target_file,
            "stdout": content,
            "stderr": read_res.get("error", "") if not read_res.get("success") else "",
            "exit_code": 0 if read_res.get("success") else 1
        }
        state.setdefault("observations", []).append(obs)
        await emit(run_id, "observation_created", "executor", obs)

        if step:
            step["status"] = "completed"
            await emit(run_id, "step_completed", "executor", {"step_id": step["id"], "status": "completed"})

        state["current_step"] = "validator"
        return state

    # SCENARIO 3: MODIFY / UPDATE OPERATION (Update acceptance demo)
    if "modify" in obj_lower or "update" in obj_lower:
        # Step A: Read existing file
        step_read = get_next_step()
        if step_read:
            step_read["status"] = "running"
            await emit(run_id, "step_started", "executor", {"step_id": step_read["id"]})

        await emit(run_id, "tool_call_started", "executor", {"tool": "read_file", "path": target_file})
        read_res = await asyncio.to_thread(execute_tool, "read_file", path=target_file)
        await emit(run_id, "tool_call_completed", "executor", read_res)
        await emit(run_id, "file_read", "executor", {"path": target_file, "success": read_res.get("success")})
        
        existing_code = read_res.get("content", "")

        # Step B: Generate updated code based on existing code + objective
        system_prompt = f"""You are updating an existing Python file in the workspace: {target_file}.
Existing content:
{existing_code}

Rules:
1. Update the implementation to satisfy the user's objective.
2. Return ONLY valid, executable Python source code.
3. Do not include markdown or ```python code fences.
4. Ensure the program prints the expected outputs to stdout."""

        user_prompt = f"Objective: {objective}"
        updated_code = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
        updated_code = clean_python_code(updated_code)

        # Step C: Write update_file
        await emit(run_id, "tool_call_started", "executor", {"tool": "update_file", "path": target_file})
        update_res = await asyncio.to_thread(execute_tool, "update_file", path=target_file, content=updated_code)
        await emit(run_id, "tool_call_completed", "executor", update_res)
        await emit(run_id, "file_updated", "executor", {
            "path": target_file,
            "lines": update_res.get("lines"),
            "diff": update_res.get("diff")
        })

        state.setdefault("artifacts", []).append({
            "type": "file",
            "path": target_file,
            "operation": "updated"
        })

        if step_read:
            step_read["status"] = "completed"
            await emit(run_id, "step_completed", "executor", {"step_id": step_read["id"], "status": "completed"})

        # Step D: Execute updated program
        step_exec = get_next_step()
        if step_exec:
            step_exec["status"] = "running"
            await emit(run_id, "step_started", "executor", {"step_id": step_exec["id"]})

        cmd = f'"{python_exe}" "{target_file}"'
        await emit(run_id, "command_started", "executor", {"command": cmd})
        cmd_res = await asyncio.to_thread(execute_tool, "run_command", command=cmd, timeout=20)
        await emit(run_id, "command_completed", "executor", cmd_res)

        obs = {
            "filename": target_file,
            "command": cmd_res.get("command", cmd),
            "stdout": cmd_res.get("stdout", ""),
            "stderr": cmd_res.get("stderr", ""),
            "exit_code": cmd_res.get("exit_code", 1),
            "duration": cmd_res.get("duration", 0)
        }
        state.setdefault("observations", []).append(obs)
        await emit(run_id, "observation_created", "executor", obs)

        if step_exec:
            step_exec["status"] = "completed"
            await emit(run_id, "step_completed", "executor", {"step_id": step_exec["id"], "status": "completed"})

        state["current_step"] = "validator"
        return state

    # SCENARIO 4: CREATE & EXECUTE OPERATION (Create factorial / Phase 3 print 1 to 10)
    # Step A: Check / inspect workspace
    step_create = get_next_step()
    if step_create:
        step_create["status"] = "running"
        await emit(run_id, "step_started", "executor", {"step_id": step_create["id"]})

    # Check if target file already exists
    read_check = await asyncio.to_thread(execute_tool, "read_file", path=target_file)
    file_exists = read_check.get("success", False)

    # Step B: Author code
    system_prompt = f"""Generate the Python implementation required to satisfy the objective.
Target file: {target_file}

Rules:
1. Return ONLY valid, executable Python source code.
2. Do not include markdown or ```python code fences.
3. If the objective requires computing a value (e.g. recursive factorial for 5) or printing numbers, ensure the program runs and prints the result to stdout.
4. Self-contained and runnable under Python 3."""

    user_prompt = f"Objective: {objective}\nContext: {json.dumps(state.get('research', []))}"
    code = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
    code = clean_python_code(code)

    # Step C: Create file via tool
    await emit(run_id, "tool_call_started", "executor", {"tool": "create_file", "path": target_file})
    create_res = await asyncio.to_thread(execute_tool, "create_file", path=target_file, content=code)
    await emit(run_id, "tool_call_completed", "executor", create_res)
    await emit(run_id, "file_created", "executor", {
        "path": target_file,
        "lines": create_res.get("lines"),
        "bytes_written": create_res.get("bytes_written")
    })

    state.setdefault("artifacts", []).append({
        "type": "file",
        "path": target_file,
        "operation": "created"
    })

    if step_create:
        step_create["status"] = "completed"
        await emit(run_id, "step_completed", "executor", {"step_id": step_create["id"], "status": "completed"})

    # Step D: Run command via tool
    step_exec = get_next_step()
    if step_exec:
        step_exec["status"] = "running"
        await emit(run_id, "step_started", "executor", {"step_id": step_exec["id"]})

    cmd = f'"{python_exe}" "{target_file}"'
    await emit(run_id, "command_started", "executor", {"command": cmd})
    cmd_res = await asyncio.to_thread(execute_tool, "run_command", command=cmd, timeout=20)
    await emit(run_id, "command_completed", "executor", cmd_res)

    obs = {
        "filename": target_file,
        "command": cmd_res.get("command", cmd),
        "stdout": cmd_res.get("stdout", ""),
        "stderr": cmd_res.get("stderr", ""),
        "exit_code": cmd_res.get("exit_code", 1),
        "duration": cmd_res.get("duration", 0)
    }
    state.setdefault("observations", []).append(obs)
    await emit(run_id, "observation_created", "executor", obs)

    if step_exec:
        step_exec["status"] = "completed"
        await emit(run_id, "step_completed", "executor", {"step_id": step_exec["id"], "status": "completed"})

    state["current_step"] = "validator"
    return state
