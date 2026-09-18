import json
import asyncio
from typing import List, Dict, Any

from app.events import emit
from app.llm.router import call_groq

def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

async def orchestrator_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "orchestrator", {"summary": "Analyzing intent and building action-oriented execution plan."})
    
    context_summary = ""
    if state.get("conversation_context"):
        turns = state["conversation_context"]
        context_summary = f"\nPrevious Conversation Turns:\n{json.dumps(turns, indent=2)}"

    system_prompt = """You are the Orchestrator for Fraiday, an action-oriented autonomous workspace runtime agent.
You decompose user objectives into concrete, action-oriented execution steps.

Available Actions:
- inspect_workspace: Check directory contents or discover files
- read_file: Inspect existing file content
- create_file: Author a new source code or configuration file
- update_file: Modify existing file content based on new requirements
- delete_file: Remove a file (subject to safety policy)
- run_command: Execute safe commands in workspace (e.g. python, node, git)
- validate_result: Verify execution exit codes and stdout results

Return ONLY valid JSON matching this schema:
{
  "steps": [
    {
      "id": "step_1",
      "agent": "researcher" or "executor" or "validator",
      "action": "inspect_workspace" or "read_file" or "create_file" or "update_file" or "delete_file" or "run_command" or "validate_result",
      "description": "Concise, action-oriented description of the step"
    }
  ]
}
Do not include markdown or conversational text."""

    user_prompt = f"Objective: {state['objective']}\nWorkspace: {state.get('workspace', {}).get('root_path')}{context_summary}"
    
    try:
        response = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
        plan_data = json.loads(clean_json(response))
    except Exception:
        system_prompt += "\nReturn ONLY valid JSON. No markdown."
        response = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
        try:
            plan_data = json.loads(clean_json(response))
        except Exception as e:
            # Fallback to sensible action plan if LLM output fails parsing
            obj = state['objective'].lower()
            if "delete" in obj:
                plan_data = {"steps": [
                    {"id": "step_1", "agent": "executor", "action": "delete_file", "description": "Check safety policy and request approval for file deletion"},
                    {"id": "step_2", "agent": "validator", "action": "validate_result", "description": "Verify deletion policy enforcement"}
                ]}
            elif "show" in obj or "read" in obj or "inside" in obj:
                plan_data = {"steps": [
                    {"id": "step_1", "agent": "executor", "action": "read_file", "description": "Inspect and read file content from workspace"},
                    {"id": "step_2", "agent": "validator", "action": "validate_result", "description": "Validate file content read"}
                ]}
            elif "modify" in obj or "update" in obj:
                plan_data = {"steps": [
                    {"id": "step_1", "agent": "researcher", "action": "read_file", "description": "Inspect existing implementation in workspace"},
                    {"id": "step_2", "agent": "executor", "action": "update_file", "description": "Update source code with new requirements"},
                    {"id": "step_3", "agent": "executor", "action": "run_command", "description": "Execute updated program in workspace"},
                    {"id": "step_4", "agent": "validator", "action": "validate_result", "description": "Validate execution output"}
                ]}
            else:
                plan_data = {"steps": [
                    {"id": "step_1", "agent": "researcher", "action": "inspect_workspace", "description": "Inspect workspace context"},
                    {"id": "step_2", "agent": "executor", "action": "create_file", "description": "Create required source file"},
                    {"id": "step_3", "agent": "executor", "action": "run_command", "description": "Execute script using Python runtime"},
                    {"id": "step_4", "agent": "validator", "action": "validate_result", "description": "Validate program execution"}
                ]}
            
    steps = plan_data.get("steps", [])
    for i, step in enumerate(steps):
        if "status" not in step:
            step["status"] = "pending"
        if "id" not in step:
            step["id"] = f"step_{i+1}"
            
    state["plan"] = steps
    await emit(state["run_id"], "plan_created", "orchestrator", {"steps": steps})
    
    state["current_step"] = "researcher"
    return state
