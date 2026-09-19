import os
import re
import asyncio
from app.events import emit
from app.workspace.manager import get_workspace_manager
from app.workspace.artifact_cleaner import extract_and_validate_artifact

def extract_expected_outputs(objective: str) -> list:
    """
    Extracts explicit required output strings enclosed in single/double quotes.
    E.g. "Create context_test.py that prints 'Hello from Fraiday'." -> ['Hello from Fraiday']
    "Modify it to print 'Hello from Fraiday Context'." -> ['Hello from Fraiday Context']
    """
    matches = re.findall(r"['\"]([^'\"]+)['\"]", objective)
    filtered = [m for m in matches if not m.endswith(".py") and not m.endswith(".json") and not m.endswith(".csv") and not m.endswith(".html") and not m.endswith(".css")]
    return filtered

async def validator_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "validator", {"summary": "Validating workspace outcome against objective intent."})
    
    current_step_obj = next((s for s in state.get("plan", []) if s.get("agent") == "validator" and s.get("status") == "pending"), None)
    if current_step_obj:
        current_step_obj["status"] = "running"
        await emit(state["run_id"], "step_started", "validator", {"step_id": current_step_obj["id"]})

    objective = state.get("objective", "")
    expected_strings = extract_expected_outputs(objective)

    if state.get("approval_required"):
        result = {
            "valid": True,
            "status": "approval_required",
            "reason": "Security policy enforced: destructive operation requires explicit user approval."
        }
    else:
        observations = state.get("observations", [])
        artifacts = state.get("artifacts", [])
        ws = get_workspace_manager()

        # Check for static web artifact tasks (.html, .css)
        html_artifacts = [a for a in artifacts if a.get("path", "").endswith(".html") or a.get("path", "").endswith(".htm")]
        css_artifacts = [a for a in artifacts if a.get("path", "").endswith(".css")]

        if html_artifacts or ("html" in objective.lower() and "fraiday_runtime_test" in objective.lower()):
            html_name = html_artifacts[0]["path"] if html_artifacts else "fraiday_runtime_test.html"
            css_name = css_artifacts[0]["path"] if css_artifacts else "styles.css"

            full_html = ws.resolve_path(html_name)
            full_css = ws.resolve_path(css_name)

            if os.path.exists(full_html):
                with open(full_html, "r", encoding="utf-8", errors="replace") as f:
                    html_content = f.read()

                valid_html, _, html_err = extract_and_validate_artifact(html_name, html_content)
                if not valid_html:
                    result = {"valid": False, "reason": f"HTML validation failed for {html_name}: {html_err}"}
                else:
                    missing = []
                    if "hello from fraiday" in objective.lower() and "hello from fraiday" not in html_content.lower():
                        missing.append("Hello from Fraiday")
                    if "autonomous workspace test" in objective.lower() and "autonomous workspace test" not in html_content.lower():
                        missing.append("Autonomous workspace test")
                    if "run test" in objective.lower() and "run test" not in html_content.lower():
                        missing.append("Run Test")

                    if missing:
                        result = {"valid": False, "reason": f"HTML file '{html_name}' missing expected element: '{missing[0]}'."}
                    elif "styles.css" in html_content and not os.path.exists(full_css):
                        result = {"valid": False, "reason": f"HTML references 'styles.css' but local stylesheet file '{css_name}' was not found."}
                    else:
                        if os.path.exists(full_css):
                            with open(full_css, "r", encoding="utf-8", errors="replace") as f:
                                css_content = f.read()
                            valid_css, _, css_err = extract_and_validate_artifact(css_name, css_content)
                            if not valid_css:
                                result = {"valid": False, "reason": f"CSS validation failed for {css_name}: {css_err}"}
                            else:
                                result = {"valid": True, "reason": "Static web artifacts (HTML & CSS) verified successfully in workspace."}
                        else:
                            result = {"valid": True, "reason": f"HTML artifact '{html_name}' verified successfully."}
            else:
                result = {"valid": False, "reason": f"Target HTML artifact '{html_name}' does not exist in workspace."}
        elif not observations:
            result = {"valid": False, "reason": "No execution observations recorded."}
        else:
            proc_obs = [o for o in observations if "exit_code" in o]
            if not proc_obs:
                last_obs = observations[-1]
                if last_obs.get("tool") in ["read_file", "create_file"] and (last_obs.get("stdout") or last_obs.get("filename")):
                    result = {"valid": True, "reason": "File content successfully processed and verified in workspace."}
                else:
                    result = {"valid": False, "reason": "No execution observation found."}
            else:
                last_proc = proc_obs[-1]
                exit_code = last_proc.get("exit_code", 1)
                stdout = last_proc.get("stdout", "").strip()

                if exit_code != 0:
                    result = {
                        "valid": False,
                        "reason": f"Process exited with non-zero exit code ({exit_code}). Stderr: {last_proc.get('stderr')}"
                    }
                else:
                    all_stdouts = "\n".join([o.get("stdout", "") for o in proc_obs])
                    failed_reqs = []
                    if expected_strings:
                        for req in expected_strings:
                            if req not in all_stdouts:
                                failed_reqs.append(req)

                    if failed_reqs:
                        result = {
                            "valid": False,
                            "reason": f"Process execution output '{stdout}' failed objective requirement validation: missing expected text '{failed_reqs[0]}'."
                        }
                    else:
                        result = {
                            "valid": True,
                            "reason": "Process exited with code 0 and execution output satisfied objective requirements."
                        }

    state.setdefault("validation_results", []).append(result)
    await emit(state["run_id"], "validation_result", "validator", result)
    
    if current_step_obj:
        current_step_obj["status"] = "completed"
        await emit(state["run_id"], "step_completed", "validator", {"step_id": current_step_obj["id"], "status": "completed"})

    if result.get("valid"):
        state["current_step"] = "end"
    else:
        state["current_step"] = "recovery"
    return state
