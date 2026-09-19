from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.db.database import db
from app.tools.terminal import get_terminal_manager

router = APIRouter(prefix="/terminals", tags=["terminals"])

class KillTerminalRequest(BaseModel):
    pass

@router.get("")
def list_terminals():
    # Sync with DB and actual processes
    return get_terminal_manager().list_terminals()

@router.post("/{t_id}/kill")
def kill_terminal(t_id: str):
    success = get_terminal_manager().kill_terminal(t_id)
    if not success:
        raise HTTPException(status_code=404, detail="Terminal not found or already dead")
    return {"success": True}

@router.get("/{t_id}/logs")
def get_terminal_logs(t_id: str):
    logs = get_terminal_manager().get_logs(t_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return {"logs": logs}
