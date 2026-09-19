import os
import re
import json
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
    filtered = [m for m in matches if not m.endswith(".py") and not m.endswith(".json") and not m.endswith(".csv") and not m.endswith(".html") and not m.endswith(".css") and not m.endswith(".js") and not m.endswith(".txt") and not m.endswith(".md")]
    return filtered

async def validator_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "validator", {"summary": "Validating workspace outcome against objective intent."})
    
    current_step_obj = next((s for s in state.get("plan", []) if s.get("agent") == "validator" and s.get("status") == "pending"), None)
    if current_step_obj:
        current_step_obj["status"] = "running"
        await emit(state["run_id"], "step_started", "validator", {"step_id": current_step_obj["id"]})

    objective = state.get("objective", "")
    obj_lower = objective.lower()
    expected_strings = extract_expected_outputs(objective)
    ws = get_workspace_manager()
    observations = state.get("observations", [])
    artifacts = state.get("artifacts", [])

    result = None

    # 1. Approval Required (Human In The Loop Pause)
    if state.get("approval_required"):
        result = {
            "valid": True,
            "status": "approval_required",
            "reason": "Security policy enforced: destructive operation requires explicit user approval."
        }

    # 2. Pure Inspection Task Validation
    if not result:
        is_pure_inspection = any(k in obj_lower for k in ["list the files", "list files", "inspect workspace", "show files", "show directory", "list directory"]) and not any(k in obj_lower for k in ["create", "generate", "write", "build", "make", "author", "update", "modify", "delete", "remove", "add"])
        if is_pure_inspection:
            inspect_obs = [o for o in observations if o.get("action") in ["LIST_DIRECTORY", "READ_FILE", "INSPECT_RUNTIME"] or o.get("tool") in ["list_directory", "read_file", "inspect_runtime"]]
            if inspect_obs and any(o.get("success", True) for o in inspect_obs):
                result = {
                    "valid": True,
                    "reason": "Workspace inspection completed successfully."
                }

    # 3. Static Web Application (.html, .css, .js) Validation
    if not result and ("html" in obj_lower or "css" in obj_lower or "web" in obj_lower or "dashboard" in obj_lower or "ecommerce" in obj_lower or "e-commerce" in obj_lower or any(a.get("path", "").endswith(".html") for a in artifacts)):
        html_artifacts = [a["path"] for a in artifacts if a.get("path", "").endswith(".html") or a.get("path", "").endswith(".htm")]
        
        if not html_artifacts:
            m = re.search(r'\b([a-zA-Z0-9_\-]+\.html)\b', objective, re.IGNORECASE)
            html_name = m.group(1) if m else ("ecommerce.html" if "ecommerce" in obj_lower or "e-commerce" in obj_lower else ("college_dashboard.html" if "dashboard" in obj_lower else "index.html"))
        else:
            html_name = html_artifacts[0]

        full_html = ws.resolve_path(html_name)

        if not os.path.exists(full_html):
            result = {"valid": False, "status": "FAILED", "reason": f"Target HTML artifact '{html_name}' does not exist in workspace."}
        else:
            with open(full_html, "r", encoding="utf-8", errors="replace") as f:
                html_content = f.read()

            valid_html, _, html_err = extract_and_validate_artifact(html_name, html_content)
            if not valid_html:
                result = {"valid": False, "status": "FAILED", "reason": f"HTML validation failed for {html_name}: {html_err}"}
            else:
                # A. Cross-File Asset Link Parsing & Validation
                css_refs = re.findall(r'<link[^>]+href=["\']([^"\']+\.css)["\']', html_content, re.IGNORECASE)
                css_refs += re.findall(r'<link[^>]+rel=["\']stylesheet["\'][^>]+href=["\']([^"\']+\.css)["\']', html_content, re.IGNORECASE)
                css_refs = list(set(css_refs))

                js_refs = re.findall(r'<script[^>]+src=["\']([^"\']+\.js)["\']', html_content, re.IGNORECASE)
                js_refs = list(set(js_refs))

                # Validate referenced CSS assets
                for css_ref in css_refs:
                    css_path = ws.resolve_path(css_ref)
                    if not os.path.exists(css_path):
                        result = {"valid": False, "status": "INCOMPLETE", "reason": f"Cross-file link validation failed: HTML references stylesheet '{css_ref}' but file does not exist in workspace."}
                        break
                    with open(css_path, "r", encoding="utf-8", errors="replace") as f:
                        css_body = f.read().strip()
                    if len(css_body) < 50 or "{" not in css_body:
                        result = {"valid": False, "status": "INCOMPLETE", "reason": f"CSS stylesheet '{css_ref}' is minimal or empty."}
                        break

                # Validate referenced JS assets
                if not result and js_refs:
                    for js_ref in js_refs:
                        js_path = ws.resolve_path(js_ref)
                        if not os.path.exists(js_path):
                            result = {"valid": False, "status": "INCOMPLETE", "reason": f"Cross-file link validation failed: HTML references script '{js_ref}' but file does not exist in workspace."}
                            break
                        with open(js_path, "r", encoding="utf-8", errors="replace") as f:
                            js_body = f.read().strip()
                        if len(js_body) < 30:
                            result = {"valid": False, "status": "INCOMPLETE", "reason": f"JavaScript file '{js_ref}' is minimal or empty."}
                            break

                # B. Objective Completeness Gate
                if not result:
                    missing = [exp for exp in expected_strings if exp.lower() not in html_content.lower()]
                    
                    if "ecommerce" in obj_lower or "e-commerce" in obj_lower or "shop" in obj_lower or "cart" in obj_lower:
                        required_elements = ["cart", "product", "price"]
                        for req_el in required_elements:
                            if req_el not in html_content.lower():
                                missing.append(req_el)

                    if missing:
                        result = {"valid": False, "status": "INCOMPLETE", "reason": f"HTML artifact '{html_name}' is incomplete: missing required section or element '{missing[0]}'."}
                    else:
                        result = {"valid": True, "status": "COMPLETE", "reason": "Static web application (HTML, CSS, JS) and cross-file relationships validated successfully."}

    # 4. Script Process Execution & Web Server Validation
    if not result:
        proc_obs = [o for o in observations if o.get("action") in ["RUN_COMMAND", "EXECUTE", "START_SERVER", "WEB_PREVIEW_SERVER"] or o.get("tool") in ["run_command", "start_server"] or "exit_code" in o]
        if proc_obs and any("command" in o or "exit_code" in o or "status" in o for o in proc_obs):
            last_proc = proc_obs[-1]
            exit_code = last_proc.get("exit_code", 1)
            stdout = last_proc.get("stdout", "").strip()
            is_server = (
                last_proc.get("action") in ["START_SERVER", "WEB_PREVIEW_SERVER"] or
                last_proc.get("kind") == "server_started" or
                last_proc.get("status") == "server_started" or
                last_proc.get("tool") == "start_server"
            )

            if is_server:
                if last_proc.get("success", True) or exit_code == 0:
                    url = last_proc.get("url") or "http://localhost:5500"
                    result = {
                        "valid": True,
                        "status": "COMPLETE",
                        "reason": f"Web preview server active and validated successfully at {url}."
                    }
                else:
                    result = {
                        "valid": False,
                        "status": "FAILED",
                        "reason": f"Web preview server failed to start: {last_proc.get('stderr') or 'Process launch error'}"
                    }
            elif exit_code != 0:
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

    # 5. Data / Document Artifact (.json, .csv, .md, .txt) Validation
    if not result:
        target_file = None
        for a in artifacts:
            p = a.get("path", "")
            if any(p.endswith(ext) for ext in [".json", ".csv", ".md", ".txt", ".js", ".ts"]):
                target_file = p
                break

        if not target_file:
            m = re.search(r'\b([a-zA-Z0-9_\-]+\.(?:json|csv|md|txt|js|ts))\b', objective, re.IGNORECASE)
            if m:
                target_file = m.group(1)

        if target_file:
            full_path = ws.resolve_path(target_file)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                valid_art, _, art_err = extract_and_validate_artifact(target_file, content)
                if not valid_art:
                    result = {"valid": False, "reason": f"Artifact validation failed for '{target_file}': {art_err}"}
                else:
                    if target_file.endswith(".json"):
                        try:
                            json.loads(content)
                        except Exception as e:
                            result = {"valid": False, "reason": f"JSON artifact '{target_file}' is invalid: {e}"}
                    
                    if not result:
                        missing = [exp for exp in expected_strings if exp.lower() not in content.lower()]
                        if missing:
                            result = {"valid": False, "reason": f"Artifact '{target_file}' missing expected content: '{missing[0]}'."}
                        else:
                            result = {"valid": True, "reason": f"Artifact '{target_file}' verified successfully."}
            else:
                result = {"valid": False, "reason": f"Target artifact '{target_file}' does not exist in workspace."}

    # 6. Destructive Operation Validation
    if not result and ("delete" in obj_lower or "remove" in obj_lower):
        del_obs = [o for o in observations if o.get("action") == "DELETE_FILE" or o.get("tool") == "delete_file"]
        if del_obs:
            result = {"valid": True, "reason": "File deletion step completed."}

    # 7. Generic Creation / Workspace Operation Fallback Validation
    if not result:
        creation_obs = [o for o in observations if o.get("action") in ["CREATE_FILE", "UPDATE_FILE", "WRITE_FILE"] or o.get("tool") in ["create_file", "update_file"]]
        if creation_obs and any(o.get("success", True) for o in creation_obs):
            result = {"valid": True, "reason": "Workspace artifact operation completed successfully."}
        else:
            result = {"valid": False, "reason": "No execution observation found."}

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
