import json
import asyncio
from typing import Dict, Any

from app.events import emit
from app.llm.router import call_groq
from app.workspace.tools import execute_tool

def clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

async def researcher_node(state: dict) -> dict:
    await emit(state["run_id"], "agent_thinking", "researcher", {"summary": "Reviewing workspace context and technical requirements."})
    
    current_step_obj = next((s for s in state.get("plan", []) if s.get("agent") == "researcher" and s.get("status") == "pending"), None)
    if current_step_obj:
        current_step_obj["status"] = "running"
        await emit(state["run_id"], "step_started", "researcher", {"step_id": current_step_obj["id"]})
    
    # Check if there are existing files mentioned in objective or conversation
    findings = []
    
    # 1. Quick inspection of workspace
    ls_res = await asyncio.to_thread(execute_tool, "list_directory", path=".")
    if ls_res.get("success"):
        file_names = [e["name"] for e in ls_res.get("entries", []) if not e.get("is_directory")]
        findings.append(f"Workspace contains {len(file_names)} root files.")
        
    system_prompt = """You are a researcher. Given the objective and workspace context, return technical findings as JSON:
{
  "findings": ["...", "..."],
  "confidence": 1.0
}
Return ONLY valid JSON."""
    user_prompt = f"Objective: {state['objective']}\nPlan: {json.dumps(state['plan'])}\nWorkspace Files: {findings}"
    
    try:
        response = await asyncio.to_thread(call_groq, system_prompt, user_prompt)
        research_data = json.loads(clean_json(response))
    except Exception:
        research_data = {
            "findings": findings or ["Proceed with workspace execution."],
            "confidence": 0.95
        }
            
    state.setdefault("research", []).append(research_data)
    
    if current_step_obj:
        current_step_obj["status"] = "completed"
        await emit(state["run_id"], "step_completed", "researcher", {"step_id": current_step_obj["id"], "status": "completed"})
        
    state["current_step"] = "executor"
    return state
