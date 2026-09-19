import re
import json
import asyncio
from typing import List, Dict, Any

from app.events import emit
from app.llm.router import call_groq
from app.workspace.manager import get_workspace_manager

def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def determine_target_filename(objective: str, context: List[dict] = None) -> str:
    m = re.search(r'\b([a-zA-Z0-9_\-]+\.(?:py|html|css|js|ts|json|csv|md|txt))\b', objective, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    
    obj_lower = objective.lower()
    if "factorial" in obj_lower:
        return "factorial.py"
    if "fibonacci" in obj_lower:
        return "fibonacci.py"
    if "csv" in obj_lower and "json" in obj_lower:
        return "csv_to_json.py"
    if "college" in obj_lower or "dashboard" in obj_lower:
        return "college_dashboard.html"

    # Check referential updates (pronoun / follow-up reference to previous file in context)
    is_referential_update = any(k in obj_lower for k in [
        "that same file", "that file", "the file", "modify it", "update it",
        "modify this", "update this", "modify that", "update that", "then modify", "then update",
        "same file", "previous file"
    ]) or (re.search(r'\b(it|this|that)\b', obj_lower) and context)

    if is_referential_update and context:
        for turn in reversed(context):
            for art in turn.get("artifacts", []):
                p = art.get("path")
                if p and not p.endswith(".json"):
                    return p

    if "hello world" in obj_lower or "hello fraiday" in obj_lower or "hello" in obj_lower:
        return "hello.py"
    if "html" in obj_lower:
        return "index.html"
    if "css" in obj_lower:
        return "styles.css"
    if "javascript" in obj_lower or " js " in f" {obj_lower} ":
        return "hello.js"
    if "json" in obj_lower:
        return "config.json"
    if "csv" in obj_lower:
        return "data.csv"
    if "readme" in obj_lower or "markdown" in obj_lower:
        return "README.md"
    if "txt" in obj_lower or "notes" in obj_lower:
        return "notes.txt"

    return "hello.py" if "python" in obj_lower or "script" in obj_lower else "main.py"

def build_dynamic_fallback_plan(objective: str, existing_files: List[str], context: List[dict] = None) -> List[Dict[str, Any]]:
    obj_lower = objective.lower()
    steps = []

    steps.append({
        "id": "step_1",
        "description": "Inspect workspace directory to discover existing files and inputs.",
        "agent": "executor",
        "action": "LIST_DIRECTORY",
        "target": ".",
        "arguments": {"path": "."},
        "depends_on": [],
        "status": "pending",
        "reason": "Verify input files before proceeding with plan execution."
    })

    prev_step_id = "step_1"

    py_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.py)\b', objective, re.IGNORECASE)))
    csv_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.csv)\b', objective, re.IGNORECASE)))
    txt_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.txt)\b', objective, re.IGNORECASE)))
    json_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.json)\b', objective, re.IGNORECASE)))
    html_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.html)\b', objective, re.IGNORECASE)))
    css_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.css)\b', objective, re.IGNORECASE)))
    js_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.(?:js|ts))\b', objective, re.IGNORECASE)))
    md_files = list(set(re.findall(r'\b([a-zA-Z0-9_\-]+\.md)\b', objective, re.IGNORECASE)))

    # Pure inspection task check
    is_pure_inspection = any(k in obj_lower for k in ["list the files", "list files", "inspect workspace", "show files", "show directory", "list directory"]) and not any(k in obj_lower for k in ["create", "generate", "write", "build", "make", "author", "update", "modify", "delete", "remove", "add"])
    if is_pure_inspection:
        return steps

    # Format / target inference if implicit
    is_web_obj = any(k in obj_lower for k in ["html", "css", "web", "dashboard", "ecommerce", "e-commerce", "portfolio", "store", "shop"])
    if is_web_obj:
        if not html_files:
            if "ecommerce" in obj_lower or "e-commerce" in obj_lower or "store" in obj_lower or "shop" in obj_lower:
                html_files = ["ecommerce.html"]
            elif "college" in obj_lower or "dashboard" in obj_lower:
                html_files = ["college_dashboard.html"]
            elif "portfolio" in obj_lower:
                html_files = ["portfolio.html"]
            else:
                html_files = ["index.html"]

        if not css_files:
            main_html = html_files[0]
            css_files = [main_html.replace(".html", ".css")]

        if not js_files and ("js" in obj_lower or "javascript" in obj_lower or "cart" in obj_lower or "filter" in obj_lower or "search" in obj_lower or "interactive" in obj_lower or "complete" in obj_lower or "ecommerce" in obj_lower or "e-commerce" in obj_lower or "dashboard" in obj_lower or "portfolio" in obj_lower):
            main_html = html_files[0]
            js_files = [main_html.replace(".html", ".js")]

    if not json_files and ("json" in obj_lower and "csv" not in obj_lower):
        json_files = ["config.json"]
    if not csv_files and ("csv" in obj_lower and "json" not in obj_lower):
        csv_files = ["data.csv"]
    if not md_files and ("readme" in obj_lower or "markdown" in obj_lower):
        md_files = ["README.md"]
    if not txt_files and ("text file" in obj_lower or "txt" in obj_lower or "notes" in obj_lower):
        txt_files = ["notes.txt"]

    has_readme = bool(md_files) or "readme" in obj_lower
    readme_target = md_files[0] if md_files else "README.md"
    main_script = py_files[0] if py_files else determine_target_filename(objective, context)

    # Delete operation
    if "delete" in obj_lower or "remove" in obj_lower:
        target_del = main_script if main_script != "main.py" else (txt_files[0] if txt_files else "temporary_test.txt")
        steps.append({
            "id": f"step_{len(steps) + 1}",
            "description": f"Delete target file '{target_del}'.",
            "agent": "executor",
            "action": "DELETE_FILE",
            "target": target_del,
            "arguments": {"path": target_del},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": "Perform safe file deletion."
        })
        return steps

    # Web static project (HTML/CSS/JS) handling
    if html_files or css_files:
        for html_f in html_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Create HTML artifact '{html_f}'.",
                "agent": "executor",
                "action": "CREATE_FILE",
                "target": html_f,
                "arguments": {"path": html_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Author {html_f} structure."
            })
            prev_step_id = step_id

        for css_f in css_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Create CSS stylesheet '{css_f}'.",
                "agent": "executor",
                "action": "CREATE_FILE",
                "target": css_f,
                "arguments": {"path": css_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Author {css_f} styles."
            })
            prev_step_id = step_id

        for js_f in js_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Create JavaScript script '{js_f}'.",
                "agent": "executor",
                "action": "CREATE_FILE",
                "target": js_f,
                "arguments": {"path": js_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Author {js_f} behavior."
            })
            prev_step_id = step_id

        for html_f in html_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Read and inspect HTML artifact '{html_f}'.",
                "agent": "executor",
                "action": "READ_FILE",
                "target": html_f,
                "arguments": {"path": html_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Inspect {html_f}."
            })
            prev_step_id = step_id

        for css_f in css_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Read and inspect CSS stylesheet '{css_f}'.",
                "agent": "executor",
                "action": "READ_FILE",
                "target": css_f,
                "arguments": {"path": css_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Inspect {css_f}."
            })
            prev_step_id = step_id

        for js_f in js_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Read and inspect JS script '{js_f}'.",
                "agent": "executor",
                "action": "READ_FILE",
                "target": js_f,
                "arguments": {"path": js_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Inspect {js_f}."
            })
        target_html = html_files[0] if html_files else "index.html"
        server_step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": server_step_id,
            "description": f"Start web application preview server for '{target_html}'.",
            "agent": "executor",
            "action": "START_SERVER",
            "target": target_html,
            "arguments": {"target": target_html, "port": 5500},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": f"Serve {target_html} locally for web preview."
        })

        return steps

    # JavaScript / TypeScript handling
    if js_files:
        for js_f in js_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Create JavaScript script '{js_f}'.",
                "agent": "executor",
                "action": "CREATE_FILE",
                "target": js_f,
                "arguments": {"path": js_f},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Author {js_f} script."
            })
            prev_step_id = step_id

            if any(k in obj_lower for k in ["run", "execute", "print"]):
                run_id = f"step_{len(steps) + 1}"
                steps.append({
                    "id": run_id,
                    "description": f"Execute JavaScript script '{js_f}'.",
                    "agent": "executor",
                    "action": "RUN_COMMAND",
                    "target": js_f,
                    "arguments": {"command": f"node {js_f}"},
                    "depends_on": [step_id],
                    "status": "pending",
                    "reason": f"Run {js_f}."
                })
                prev_step_id = run_id
        return steps

    # JSON document creation
    if json_files and not py_files:
        for jf in json_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Create JSON document '{jf}'.",
                "agent": "executor",
                "action": "CREATE_FILE",
                "target": jf,
                "arguments": {"path": jf},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Author {jf} configuration/data."
            })
            prev_step_id = step_id
            read_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": read_id,
                "description": f"Read and inspect JSON document '{jf}'.",
                "agent": "executor",
                "action": "READ_FILE",
                "target": jf,
                "arguments": {"path": jf},
                "depends_on": [step_id],
                "status": "pending",
                "reason": f"Verify {jf} content."
            })
            prev_step_id = read_id
        return steps

    # Markdown document creation
    if md_files and not py_files:
        for mf in md_files:
            step_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": step_id,
                "description": f"Create Markdown document '{mf}'.",
                "agent": "executor",
                "action": "CREATE_FILE",
                "target": mf,
                "arguments": {"path": mf},
                "depends_on": [prev_step_id],
                "status": "pending",
                "reason": f"Author {mf} documentation."
            })
            prev_step_id = step_id
            read_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": read_id,
                "description": f"Read and inspect Markdown document '{mf}'.",
                "agent": "executor",
                "action": "READ_FILE",
                "target": mf,
                "arguments": {"path": mf},
                "depends_on": [step_id],
                "status": "pending",
                "reason": f"Verify {mf} content."
            })
            prev_step_id = read_id
        return steps

    # Input data files
    input_files = csv_files + txt_files
    for inp in input_files:
        step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": step_id,
            "description": f"Verify or create input file '{inp}' in workspace.",
            "agent": "executor",
            "action": "CREATE_FILE",
            "target": inp,
            "arguments": {"path": inp},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": f"Ensure input file {inp} exists for processing."
        })
        prev_step_id = step_id

    has_update = any(k in obj_lower for k in ["update that same file", "modify that same file", "then modify", "then update", "update script", "modify script", "update it", "modify it", "update this", "modify this", "update that", "modify that"]) or (obj_lower.startswith("update ") and "csv" not in obj_lower) or (obj_lower.startswith("modify ") and "csv" not in obj_lower)
    has_create = any(k in obj_lower for k in ["create", "make", "author", "generate", "write", "build", "implement"]) or (not has_update and not (re.search(r'\b(it|this|that)\b', obj_lower) or context))

    if has_create and (py_files or not input_files or "script" in obj_lower or "python" in obj_lower):
        script_step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": script_step_id,
            "description": f"Author target Python script '{main_script}'.",
            "agent": "executor",
            "action": "CREATE_FILE",
            "target": main_script,
            "arguments": {"path": main_script},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": f"Create {main_script} implementation."
        })
        prev_step_id = script_step_id

        run_step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": run_step_id,
            "description": f"Execute Python script '{main_script}'.",
            "agent": "executor",
            "action": "RUN_COMMAND",
            "target": main_script,
            "arguments": {"command": f"python {main_script}"},
            "depends_on": [script_step_id],
            "status": "pending",
            "reason": f"Run {main_script}."
        })
        prev_step_id = run_step_id

    if has_update:
        upd_step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": upd_step_id,
            "description": f"Update target script '{main_script}' with new requirements.",
            "agent": "executor",
            "action": "UPDATE_FILE",
            "target": main_script,
            "arguments": {"path": main_script},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": f"Modify {main_script} implementation."
        })
        prev_step_id = upd_step_id

        run_upd_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": run_upd_id,
            "description": f"Execute updated Python script '{main_script}'.",
            "agent": "executor",
            "action": "RUN_COMMAND",
            "target": main_script,
            "arguments": {"command": f"python {main_script}"},
            "depends_on": [upd_step_id],
            "status": "pending",
            "reason": f"Run updated {main_script}."
        })
        prev_step_id = run_upd_id

    if has_readme:
        readme_step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": readme_step_id,
            "description": f"Create {readme_target} documenting project implementation and usage.",
            "agent": "executor",
            "action": "CREATE_FILE",
            "target": readme_target,
            "arguments": {"path": readme_target},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": f"Provide complete project documentation in {readme_target}."
        })
        prev_step_id = readme_step_id

    for jf in json_files:
        val_step_id = f"step_{len(steps) + 1}"
        steps.append({
            "id": val_step_id,
            "description": f"Inspect generated output JSON file '{jf}'.",
            "agent": "executor",
            "action": "READ_FILE",
            "target": jf,
            "arguments": {"path": jf},
            "depends_on": [prev_step_id],
            "status": "pending",
            "reason": f"Verify output file {jf} content."
        })
        prev_step_id = val_step_id

    return steps

def validate_and_repair_plan(steps: List[Dict[str, Any]], objective: str, existing_files: List[str], context: List[dict] = None) -> List[Dict[str, Any]]:
    """
    Enforces the plan contract.
    If the objective requests creation, modification, or execution work,
    the plan MUST contain at least one work-producing or executing step (CREATE_FILE, UPDATE_FILE, DELETE_FILE, RUN_COMMAND).
    If it contains only inspection steps, it is repaired using fallback plan generation.
    """
    obj_lower = objective.lower()
    work_keywords = ["create", "generate", "write", "build", "implement", "make", "author", "update", "modify", "fix", "run", "execute", "test", "convert", "delete", "remove", "add"]
    format_terms = ["html", "css", "js", "javascript", "json", "csv", "python", "py", "md", "txt", "readme", "script"]

    has_work_intent = any(k in obj_lower for k in work_keywords) or any(f in obj_lower for f in format_terms)
    is_pure_inspection = any(k in obj_lower for k in ["list the files", "list files", "inspect workspace", "show files", "show directory", "list directory"]) and not any(k in obj_lower for k in ["create", "generate", "write", "build", "make", "author", "update", "modify", "delete", "remove", "add"])

    if has_work_intent and not is_pure_inspection:
        work_actions = {"CREATE_FILE", "WRITE_FILE", "UPDATE_FILE", "DELETE_FILE", "RUN_COMMAND", "EXECUTE", "START_SERVER", "WEB_PREVIEW_SERVER", "STOP_SERVER"}
        has_work_step = any(s.get("action", "").upper() in work_actions for s in steps)
        if not has_work_step:
            steps = build_dynamic_fallback_plan(objective, existing_files, context)

    # 1. Ensure plan starts with a workspace discovery step (LIST_DIRECTORY) if missing
    if steps and steps[0].get("action", "").upper() not in ["LIST_DIRECTORY", "INSPECT_WORKSPACE"]:
        steps.insert(0, {
            "id": "step_1",
            "description": "Inspect workspace directory to discover existing files and inputs.",
            "agent": "executor",
            "action": "LIST_DIRECTORY",
            "target": ".",
            "arguments": {"path": "."},
            "depends_on": [],
            "status": "pending",
            "reason": "Verify input files before proceeding with plan execution."
        })

    # Re-index step IDs & dependencies cleanly
    for i, s in enumerate(steps):
        old_id = s.get("id")
        new_id = f"step_{i+1}"
        s["id"] = new_id
        if i == 0:
            s["depends_on"] = []
        else:
            s["depends_on"] = [f"step_{i}"]

    # 2. For file creation/update steps without a subsequent READ_FILE or RUN_COMMAND step, append READ_FILE
    last_step = steps[-1] if steps else None
    if last_step and last_step.get("action", "").upper() in ["CREATE_FILE", "UPDATE_FILE", "WRITE_FILE"]:
        target = last_step.get("target") or last_step.get("arguments", {}).get("path")
        if target and not target.endswith(".py"):
            read_id = f"step_{len(steps) + 1}"
            steps.append({
                "id": read_id,
                "description": f"Read and inspect artifact '{target}'.",
                "agent": "executor",
                "action": "READ_FILE",
                "target": target,
                "arguments": {"path": target},
                "depends_on": [last_step["id"]],
                "status": "pending",
                "reason": f"Inspect {target} content."
            })

    return steps

async def orchestrator_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "orchestrator", {"summary": "Analyzing objective and building action-oriented execution plan."})

    objective = state["objective"]
    context = state.get("conversation_context", [])
    ws = get_workspace_manager()

    dir_info = ws.list_directory(".")
    existing_files = [e["name"] for e in dir_info.get("entries", []) if not e.get("is_directory")]

    research_findings = state.get("research", [])
    research_summary = ""
    if research_findings:
        accepted = [r for r in research_findings if r.get("status") == "accepted"]
        if accepted:
            research_summary = "\nAccepted Knowledge Base Findings:\n" + json.dumps(accepted, indent=2)

    context_summary = ""
    if context:
        context_summary = f"\nPrevious Conversation Turns:\n{json.dumps(context, indent=2)}"

    system_prompt = f"""You are Fraiday's Dynamic Action Orchestrator.
Decompose the user's objective into a structured, dependency-aware plan of execution steps.

Available Controlled Actions:
- LIST_DIRECTORY: Inspect workspace files (arguments: {{"path": "."}})
- READ_FILE: Inspect existing file content (arguments: {{"path": "<filename>"}})
- CREATE_FILE: Author a new source code or configuration file (arguments: {{"path": "<filename>"}})
- UPDATE_FILE: Update an existing file (arguments: {{"path": "<filename>"}})
- DELETE_FILE: Remove a file subject to safety policy (arguments: {{"path": "<filename>"}})
- RUN_COMMAND: Execute safe command in workspace (arguments: {{"command": "<cmd>"}})
- INSPECT_RUNTIME: Inspect available Python runtimes

Existing Workspace Files: {json.dumps(existing_files)}
{research_summary}
{context_summary}

Rules:
1. Every step MUST include: id, description, agent ("executor"), action, target, arguments, depends_on (list of step ids), status ("pending").
2. Ensure steps reflect true dependencies (e.g. creating input data before running script).
3. Return ONLY a JSON object with this schema:
{{
  "steps": [
    {{
      "id": "step_1",
      "description": "...",
      "agent": "executor",
      "action": "LIST_DIRECTORY" | "READ_FILE" | "CREATE_FILE" | "UPDATE_FILE" | "DELETE_FILE" | "RUN_COMMAND",
      "target": "<filename>",
      "arguments": {{...}},
      "depends_on": [],
      "status": "pending",
      "reason": "..."
    }}
  ]
}}
Do NOT include markdown or chain-of-thought."""

    user_prompt = f"Objective: {objective}"

    plan_data = None
    try:
        response = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
        plan_data = json.loads(clean_json(response))
    except Exception:
        plan_data = None

    steps = []
    if plan_data and isinstance(plan_data, dict) and "steps" in plan_data:
        raw_steps = plan_data.get("steps", [])
        for i, s in enumerate(raw_steps):
            steps.append({
                "id": s.get("id", f"step_{i+1}"),
                "description": s.get("description", "Execute action step"),
                "agent": s.get("agent", "executor"),
                "action": s.get("action", "RUN_COMMAND"),
                "target": s.get("target", "main.py"),
                "arguments": s.get("arguments", {}),
                "depends_on": s.get("depends_on", []),
                "status": "pending",
                "reason": s.get("reason", "Objective requirement execution"),
                "result": None
            })

    if not steps:
        steps = build_dynamic_fallback_plan(objective, existing_files, context)
    else:
        steps = validate_and_repair_plan(steps, objective, existing_files, context)

    state["plan"] = steps
    await emit(state["run_id"], "plan_created", "orchestrator", {"steps": steps})

    state["current_step"] = "researcher"
    return state
