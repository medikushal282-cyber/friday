import re
from app.events import emit


def _expected_output(objective: str):
    text = objective.lower()
    patterns = [
        r"(?:output|stdout|result|returns?|print(?:s|ed)?|value)[^\\d]{0,40}(\\d+(?:\\.\\d+)?)",
        r"(?:exactly|equal(?:s| to)?)[^\\d]{0,20}(\\d+(?:\\.\\d+)?)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1)
    return None


async def validator_node(state):
    run_id = state["run_id"]
    await emit(run_id, "agent_thinking", "validator", {
        "summary": "Validating the latest execution result against the user objective."
    })

    # Conversational runs should never reach validator, but guard anyway
    if state.get("objective_type") == "conversation" or state.get("conversation_response"):
        result = {
            "valid": True,
            "status": "conversational",
            "reason": "Conversational intent does not require execution validation.",
        }
        state.setdefault("validation_results", []).append(result)
        await emit(run_id, "validation_result", "validator", result)
        state["current_step"] = "end"
        return state

    if state.get("objective_type") == "research":
        research = state.get("research", [])[-1] if state.get("research") else {}
        findings = [str(item).strip() for item in research.get("findings", []) if str(item).strip()]
        sources = research.get("sources", [])
        confidence = research.get("confidence")
        source_kind = research.get("source")
        valid = bool(findings) and confidence is not None
        if source_kind == "external" or source_kind == "web":
            valid = valid and bool(sources)
        result = {
            "valid": valid,
            "status": "research",
            "source": source_kind,
            "finding": findings[0] if findings else "",
            "sources": sources,
            "confidence": confidence,
            "reason": "Focused research finding with traceable source metadata." if valid else "Research did not produce a focused, source-backed finding.",
        }
        state.setdefault("validation_results", []).append(result)
        await emit(run_id, "validation_result", "validator", result)
        state["current_step"] = "end"
        return state

    if state.get("approval_required"):
        result = {
            "valid": True,
            "status": "approval_required",
            "reason": "Destructive operation requires explicit user approval.",
        }
    else:
        observations = state.get("observations", [])
        if not observations:
            result = {"valid": False, "reason": "No execution observations recorded."}
        else:
            obs = observations[-1]
            if obs.get("status") == "approval_required":
                result = {
                    "valid": True,
                    "status": "approval_required",
                    "reason": "Destructive operation is paused for approval.",
                }
            elif obs.get("tool") == "read_file":
                stdout = (obs.get("stdout") or "").strip()
                result = {
                    "valid": bool(stdout),
                    "reason": "File content read successfully." if stdout else "File read returned empty content.",
                }
            else:
                exit_code = obs.get("exit_code")
                stdout = (obs.get("stdout") or "").strip()
                stderr = (obs.get("stderr") or "").strip()
                # INVARIANT: non-zero exit code is always failure, regardless of stdout
                if exit_code is None:
                    result = {
                        "valid": False,
                        "reason": "Process exit code is missing; treating as failure.",
                        "exit_code": exit_code, "stderr": stderr, "stdout": stdout,
                    }
                elif exit_code != 0:
                    # Include stderr for diagnosis; never PASS on failure
                    reason = f"Process exited with non-zero exit code ({exit_code})."
                    if stderr:
                        reason += f" {stderr[:500]}"
                    result = {
                        "valid": False,
                        "reason": reason,
                        "exit_code": exit_code, "stderr": stderr, "stdout": stdout,
                    }
                elif not stdout:
                    result = {
                        "valid": False,
                        "reason": "Process exited successfully but produced no stdout.",
                        "exit_code": exit_code, "stderr": stderr, "stdout": stdout,
                    }
                else:
                    expected = _expected_output(state.get("objective", ""))
                    if expected is not None and expected not in stdout:
                        result = {
                            "valid": False,
                            "reason": f"Execution succeeded but expected output {expected!r} was not found in stdout.",
                            "exit_code": exit_code, "expected_output": expected,
                            "stderr": stderr, "stdout": stdout,
                        }
                    else:
                        result = {
                            "valid": True,
                            "reason": "Execution succeeded and satisfied the observable output requirement.",
                            "exit_code": exit_code, "expected_output": expected,
                            "stderr": stderr, "stdout": stdout,
                        }
                # HARD INVARIANT ENFORCEMENT: if exit_code !=0, valid must be False
                if obs.get("exit_code") not in (None, 0) and result.get("valid") is True:
                    result = {
                        "valid": False,
                        "reason": f"Invariant violation corrected: exit_code {obs.get('exit_code')} cannot be PASS.",
                        "exit_code": obs.get("exit_code"), "stderr": stderr, "stdout": stdout,
                    }

    state.setdefault("validation_results", []).append(result)
    await emit(run_id, "validation_result", "validator", result)

    if result.get("valid"):
        if state.get("recovery_mode"):
            target = "main.py"
            for obs in reversed(state.get("observations", [])):
                if obs.get("filename"):
                    target = obs["filename"]
                    break
            await emit(run_id, "recovery_completed", "recovery", {
                "attempt": state.get("retry_count", 1),
                "path": target,
                "exit_code": result.get("exit_code", 0),
            })
            state["recovery_mode"] = False
        state["current_step"] = "end"
        return state

    retries = int(state.get("retry_count", 0))
    max_retries = int(state.get("max_retries", 3))
    if retries >= max_retries:
        await emit(run_id, "recovery_exhausted", "recovery", {
            "retries": retries,
            "max_retries": max_retries,
        })
        state["recovery_exhausted"] = True
        state["status"] = "failed"
        state["current_step"] = "end"
        return state

    state["current_step"] = "recovery"
    return state
