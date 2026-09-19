from fastapi import APIRouter
from typing import List, Dict, Any
from app.agents.registry import get_agent_registry

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("", response_model=List[Dict[str, Any]])
def list_available_agents():
    registry = get_agent_registry()
    return registry.list_agents()
