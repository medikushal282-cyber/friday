from fastapi import APIRouter
from typing import List, Dict, Any, Optional
from app.llm.models import get_model_registry

router = APIRouter(prefix="/models", tags=["Models"])

@router.get("", response_model=List[Dict[str, Any]])
def list_available_models(compatible_only: bool = True):
    registry = get_model_registry()
    return registry.list_models(agent_compatible_only=compatible_only)
