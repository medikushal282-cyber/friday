import asyncio
import re
from app.events import emit
from app.llm.router import call_groq
from app.workspace.tools import execute_tool
from app.workspace.manager import get_workspace_manager


def _target(state):
    for obs in reversed(state.get("observations", [])):
        if obs.get("filename"):
            return obs["filename"]
        if obs.get("path") and str(obs["path"]).endswith(".py"):
            return obs["path"]
    for art in reversed(state.get("artifacts", [])):
        if art.get("path"):
            return art["path"]
    m = re.search(r"\b([A-Za-z0-9_-]+\.py)\b", state.get("objective", ""), re.I)
    return m.group(1) if m else "main.py"


def _clean(code):
    code = (code or "").strip()
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


async def recovery_node(state):
    run_id = state["run_id"]
    results = state.get("validation_results", [])
    last = results[-1] if results else {"valid": False, "reason": "No validation result"}

    if last.get("valid") or state.get("approval_required"):
        state["current_step"] = "end"
        return state

    retries = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 3))
    if retries >= max_retries:
        await emit(run_id, "recovery_exhausted", "recovery", {
            "retries": retries, "max_retries": max_retries
        })
        state["recovery_exhausted"] = True
        state["status"] = "failed"
        state["current_step"] = "end"
        return state

    target = _target(state)
    read_res = await asyncio.to_thread(execute_tool, "read_file", path=target)
    current = read_res.get("content", "")
    obs = state.get("observations", [])[-1] if state.get("observations") else {}
    error = last.get("stderr") or obs.get("stderr") or last.get("reason", "Unknown execution failure")
    attempt = retries + 1

    # SSE Event requirement: recovery_started followed by agent_thinking
    await emit(run_id, "recovery_started", "recovery", {
        "attempt": attempt, "max_retries": max_retries, "path": target, "error": error
    })
    await emit(run_id, "agent_thinking", "recovery", {
        "summary": f"Diagnosing failure and generating fix with Groq (attempt {attempt}/{max_retries})."
    })

    prompt = f"""Fix the program below so it satisfies the user's objective.
Return ONLY executable Python source code. Do not explain the fix.

Objective:
{state.get('objective', '')}

Current file:
{current}

Execution error / validation failure:
{error}
"""

    try:
        fixed = await asyncio.to_thread(
            call_groq,
            "You are an autonomous debugging agent. Diagnose the observed failure and make the smallest reliable correction. Preserve the intended behavior and ensure the requested observable output is produced. Return ONLY valid raw Python source code without markdown fences.",
            prompt,
        )
        fixed = _clean(fixed)
        if not fixed:
            raise ValueError("LLM returned empty repaired source")
    except Exception as e:
        state["retry_count"] = attempt
        state.setdefault("recovery_history", []).append({
            "attempt": attempt, "error": str(e), "status": "failed"
        })
        await emit(run_id, "recovery_failed", "recovery", {
            "attempt": attempt, "error": str(e)
        })
        if attempt >= max_retries:
            await emit(run_id, "recovery_exhausted", "recovery", {
                "retries": attempt, "max_retries": max_retries
            })
            state["recovery_exhausted"] = True
            state["status"] = "failed"
            state["current_step"] = "end"
        else:
            state["current_step"] = "recovery"
        return state

    await emit(run_id, "tool_call_started", "recovery", {
        "tool": "update_file", "path": target,
        "reason": "automatic_error_recovery", "attempt": attempt
    })
    update_res = await asyncio.to_thread(
        execute_tool, "update_file", path=target, content=fixed
    )
    await emit(run_id, "tool_call_completed", "recovery", update_res)

    if not update_res.get("success"):
        state["retry_count"] = attempt
        state.setdefault("recovery_history", []).append({
            "attempt": attempt, "status": "update_failed",
            "error": update_res.get("error")
        })
        await emit(run_id, "recovery_failed", "recovery", {
            "attempt": attempt, "error": update_res.get("error", "update_file failed")
        })
        if attempt >= max_retries:
            await emit(run_id, "recovery_exhausted", "recovery", {
                "retries": attempt, "max_retries": max_retries
            })
            state["recovery_exhausted"] = True
            state["status"] = "failed"
            state["current_step"] = "end"
        else:
            state["current_step"] = "recovery"
        return state

    await emit(run_id, "file_updated", "recovery", {
        "path": target, "reason": "automatic_error_recovery", "attempt": attempt,
        "lines": update_res.get("lines"), "diff": update_res.get("diff")
    })
    state.setdefault("artifacts", []).append({
        "type": "file", "path": target, "operation": "updated", "reason": "recovery"
    })

    ws = get_workspace_manager()
    cmd = f'"{ws.get_python_executable()}" "{target}"'
    await emit(run_id, "command_started", "recovery", {
        "command": cmd, "attempt": attempt
    })
    run_res = await asyncio.to_thread(
        execute_tool, "run_command", command=cmd, timeout=20
    )
    await emit(run_id, "command_completed", "recovery", run_res)

    new_obs = {
        "filename": target,
        "command": run_res.get("command", cmd),
        "stdout": run_res.get("stdout", ""),
        "stderr": run_res.get("stderr", ""),
        "exit_code": run_res.get("exit_code", 1),
        "duration": run_res.get("duration", 0),
        "recovery_attempt": attempt,
    }
    state.setdefault("observations", []).append(new_obs)
    state["retry_count"] = attempt
    state["recovery_mode"] = True
    state.setdefault("recovery_history", []).append({
        "attempt": attempt, "path": target, "error": error,
        "status": "rerun", "exit_code": new_obs["exit_code"]
    })
    await emit(run_id, "observation_created", "recovery", new_obs)

    state["current_step"] = "validator"
    return state
