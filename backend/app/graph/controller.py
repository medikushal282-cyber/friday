import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple

# --- SAFETY LIMIT CONSTANTS ---
MAX_AUTONOMOUS_ITERATIONS = 12
MAX_REPLANS = 3
MAX_RECOVERY_ATTEMPTS = 2

# --- DECISION ENUMS ---
DECISION_CONTINUE = "CONTINUE"
DECISION_RECOVER = "RECOVER"
DECISION_REPLAN = "REPLAN"
DECISION_VALIDATE = "VALIDATE"
DECISION_WAIT_FOR_APPROVAL = "WAIT_FOR_APPROVAL"
DECISION_COMPLETE = "COMPLETE"
DECISION_FAIL = "FAIL"

def create_structured_observation(
    action: str,
    target: str,
    success: bool,
    result_data: Optional[Dict[str, Any]] = None,
    step_id: Optional[str] = None,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    failure_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a compact, structured observation object suitable for graph state and context.
    Prevents sending unbounded tool outputs into the LLM context.
    """
    summary = ""
    if success:
        if action == "LIST_DIRECTORY":
            entries = result_data.get("entries", []) if isinstance(result_data, dict) else []
            names = [e["name"] if isinstance(e, dict) else str(e) for e in entries[:8]]
            summary = f"Discovered {len(entries)} items: {', '.join(names)}"
        elif action in ["CREATE_FILE", "UPDATE_FILE"]:
            lines = result_data.get("lines", 0) if isinstance(result_data, dict) else 0
            summary = f"File {target} written successfully ({lines} lines)"
        elif action == "READ_FILE":
            content_len = len(result_data.get("content", "")) if isinstance(result_data, dict) else 0
            summary = f"Read {content_len} bytes from {target}"
        elif action == "RUN_COMMAND":
            stdout_sample = stdout.strip()[:150]
            summary = f"Command succeeded (exit 0): {stdout_sample}"
        else:
            summary = f"Action {action} succeeded on {target}"
    else:
        err_msg = stderr.strip() or stdout.strip() or "Execution failed"
        summary = f"Action {action} failed: {err_msg[:150]}"

    obs = {
        "action": action,
        "target": target,
        "success": success,
        "summary": summary,
        "step_id": step_id,
        "exit_code": exit_code,
        "stdout": stdout[:300] if stdout else "",
        "stderr": stderr[:300] if stderr else "",
        "kind": failure_type or ("syntax_ok" if success else "command_error")
    }
    if action == "LIST_DIRECTORY" and isinstance(result_data, dict):
        obs["entries"] = [e["name"] if isinstance(e, dict) else str(e) for e in result_data.get("entries", [])]
    return obs

def detect_plan_obsolescence(plan: List[Dict[str, Any]], observations: List[Dict[str, Any]]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Inspects observations against the pending steps in current plan.
    Returns (is_obsolete: bool, obsolete_step_id: Optional[str], reason: Optional[str]).
    """
    if not plan or not observations:
        return False, None, None

    existing_files = set()
    for obs in observations:
        if obs.get("action") == "LIST_DIRECTORY" and obs.get("entries"):
            existing_files.update(obs.get("entries", []))

    if not existing_files:
        return False, None, None

    for step in plan:
        if step.get("status") in ["pending", None]:
            action = step.get("action")
            target = step.get("target")

            if action in ["CREATE_FILE", "WRITE_FILE"] and target:
                if target.endswith(".csv"):
                    matching_csv = [f for f in existing_files if f.endswith(".csv")]
                    if target in existing_files or matching_csv:
                        found_name = target if target in existing_files else matching_csv[0]
                        return True, step["id"], f"Input dataset '{found_name}' already exists in workspace; creation step is unnecessary."
                elif target.endswith(".txt"):
                    matching_txt = [f for f in existing_files if f.endswith(".txt")]
                    if target in existing_files or matching_txt:
                        found_name = target if target in existing_files else matching_txt[0]
                        return True, step["id"], f"Text input file '{found_name}' already exists in workspace; creation step is unnecessary."

    return False, None, None

def evaluate_next_decision(state: Dict[str, Any]) -> Tuple[str, str]:
    """
    Determines the next autonomous controller action decision based on bounded state limits,
    observations, failure classifications, and remaining steps.

    Returns:
        (decision: str, reason: str)
    """
    iteration_count = state.get("autonomous_iteration_count", 0)
    replan_count = state.get("replan_count", 0)
    recovery_attempts = state.get("recovery_attempts", 0)

    # 1. Enforce MAX_AUTONOMOUS_ITERATIONS safety limit
    if iteration_count >= MAX_AUTONOMOUS_ITERATIONS:
        return DECISION_FAIL, f"Safety limit reached: MAX_AUTONOMOUS_ITERATIONS ({MAX_AUTONOMOUS_ITERATIONS}) exceeded."

    # 2. Enforce Human Approval pause
    if state.get("approval_required"):
        return DECISION_WAIT_FOR_APPROVAL, "Execution paused: user approval required for policy-governed action."

    # 3. Check for execution failure in last observation
    observations = state.get("observations", [])
    last_obs = observations[-1] if observations else None
    if last_obs and not last_obs.get("success"):
        failure_kind = last_obs.get("kind", "command_error")

        if failure_kind == "permission_error":
            return DECISION_FAIL, f"Execution blocked by security policy: {last_obs.get('stderr') or 'Permission denied'}"

        if recovery_attempts >= MAX_RECOVERY_ATTEMPTS:
            if replan_count < MAX_REPLANS:
                return DECISION_REPLAN, f"Max recovery attempts ({MAX_RECOVERY_ATTEMPTS}) reached for {failure_kind}; triggering re-plan."
            else:
                return DECISION_FAIL, f"Max recovery attempts ({MAX_RECOVERY_ATTEMPTS}) and max re-plans ({MAX_REPLANS}) reached."
        else:
            return DECISION_RECOVER, f"Action failure detected ({failure_kind}); attempting autonomous recovery."

    # 4. Check for plan obsolescence (stale plan)
    plan = state.get("plan", [])
    is_obsolete, obs_step_id, obs_reason = detect_plan_obsolescence(plan, observations)
    if is_obsolete:
        if replan_count < MAX_REPLANS:
            return DECISION_REPLAN, obs_reason or "Workspace observation indicates current plan steps are obsolete."
        else:
            for s in plan:
                if s.get("id") == obs_step_id:
                    s["status"] = "skipped"
                    s["reason"] = obs_reason

    # 5. Check remaining pending steps
    plan = state.get("plan", [])
    if not plan and state.get("current_step") in ["orchestrator", "researcher"]:
        return DECISION_CONTINUE, f"Executing {state.get('current_step')} to build plan."

    pending_steps = [s for s in plan if s.get("status") in ["pending", None]]
    if pending_steps:
        return DECISION_CONTINUE, f"Proceeding with next pending step '{pending_steps[0].get('id')}'."

    # 6. No pending steps remain -> Validate final state
    val_results = state.get("validation_results", [])
    if not val_results:
        return DECISION_VALIDATE, "All plan steps finished; triggering final validation."

    last_val = val_results[-1]
    if last_val.get("valid"):
        return DECISION_COMPLETE, "All plan steps completed and final validation passed."
    else:
        if recovery_attempts < MAX_RECOVERY_ATTEMPTS:
            return DECISION_RECOVER, f"Final validation failed ({last_val.get('reason')}); triggering recovery."
        elif replan_count < MAX_REPLANS:
            return DECISION_REPLAN, f"Final validation failed; triggering autonomous re-plan."
        else:
            return DECISION_FAIL, f"Final validation failed: {last_val.get('reason')}"
