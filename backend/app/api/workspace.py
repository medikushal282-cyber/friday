from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.workspace.manager import get_workspace_manager, PathSecurityError

router = APIRouter(prefix="/workspace", tags=["workspace"])

class FileWriteRequest(BaseModel):
    path: str
    content: str

@router.get("")
def get_workspace():
    ws = get_workspace_manager()
    return ws.get_workspace_info()

@router.get("/runtime")
def get_runtime():
    ws = get_workspace_manager()
    return ws.get_runtime_info()

@router.get("/files")
def get_files(path: str = Query(default="", description="Relative path in workspace")):
    ws = get_workspace_manager()
    try:
        res = ws.list_directory(path)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error", "Failed to list files"))
        return res
    except PathSecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file")
def get_file(path: str = Query(..., description="Relative path to file in workspace")):
    ws = get_workspace_manager()
    try:
        res = ws.read_file(path)
        if not res.get("success"):
            raise HTTPException(status_code=404, detail=res.get("error", "File not found"))
        return res
    except PathSecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/file")
def post_file(req: FileWriteRequest):
    ws = get_workspace_manager()
    try:
        res = ws.write_file(req.path, req.content)
        if not res.get("success"):
            raise HTTPException(status_code=400, detail=res.get("error", "Failed to write file"))
        return res
    except PathSecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
