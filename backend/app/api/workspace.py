import os
import shutil
import subprocess
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.workspace.manager import get_workspace_manager, PathSecurityError
from app.workspace.tools import tool_run_command
from app.workspace.web_server import get_web_server_manager
from app.workspace.process_manager import get_process_registry
from app.events import emit

router = APIRouter(prefix="/workspace", tags=["workspace"])

class FileWriteRequest(BaseModel):
    path: str
    content: str

class ExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = 30
    run_id: Optional[str] = None

class PreviewStartRequest(BaseModel):
    filename: Optional[str] = "index.html"
    port: Optional[int] = 5500
    run_id: Optional[str] = None

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

@router.post("/execute")
async def execute_command(req: ExecuteRequest):
    ws = get_workspace_manager()
    cmd = req.command.strip()

    # Special handling for Java runtime check
    if cmd.startswith("javac ") or cmd.startswith("java "):
        javac_path = shutil.which("javac")
        java_path = shutil.which("java")
        if not javac_path and not java_path:
            return {
                "success": False,
                "command": cmd,
                "exit_code": 1,
                "stdout": "",
                "stderr": "Java runtime unavailable. Please install JDK/JRE to compile or run Java files.",
                "duration": 0,
                "error": {"code": "RUNTIME_UNAVAILABLE", "message": "Java runtime unavailable"}
            }

    # Special handling for Node runtime check
    if cmd.startswith("node "):
        node_path = shutil.which("node")
        if not node_path:
            return {
                "success": False,
                "command": cmd,
                "exit_code": 1,
                "stdout": "",
                "stderr": "Node.js runtime unavailable. Please install Node.js to execute JavaScript files.",
                "duration": 0,
                "error": {"code": "RUNTIME_UNAVAILABLE", "message": "Node.js runtime unavailable"}
            }

    # Use python runtime from workspace if cmd starts with python
    if cmd.startswith("python "):
        py_exec = ws.get_python_executable()
        cmd = py_exec + cmd[6:]

    result = tool_run_command(cmd, timeout=req.timeout or 30)
    
    if req.run_id:
        await emit(req.run_id, "process_completed" if result.get("success") else "process_failed", "terminal", result)

    return result

@router.post("/preview/start")
async def start_preview(req: PreviewStartRequest):
    ws = get_workspace_manager()
    server_mgr = get_web_server_manager()
    res = server_mgr.start(ws.root_path, req.port or 5500)
    
    if res.get("success"):
        file_target = req.filename or "index.html"
        res["preview_url"] = f"{res['url']}/{file_target}"
        if req.run_id:
            await emit(req.run_id, "preview_started", "web_runner", res)
    return res

@router.post("/preview/stop")
async def stop_preview(run_id: Optional[str] = None, port: Optional[int] = None):
    reg = get_process_registry()
    res = reg.stop_process(port or 5500)
    if run_id:
        await emit(run_id, "preview_stopped", "web_runner", res)
    return res

@router.get("/preview/status")
def get_preview_status():
    server_mgr = get_web_server_manager()
    return server_mgr.get_status()

class StartServerRequest(BaseModel):
    command: Optional[str] = None
    target: Optional[str] = "index.html"
    port: Optional[int] = 5500
    run_id: Optional[str] = None

class StopServerRequest(BaseModel):
    process_id: Optional[str] = None
    port: Optional[int] = None
    run_id: Optional[str] = None

@router.post("/start_server")
async def start_server_endpoint(req: StartServerRequest):
    ws = get_workspace_manager()
    reg = get_process_registry()
    if req.command:
        res = reg.start_long_running_process(req.command, ws.root_path, req.port, req.run_id or "")
    else:
        res = reg.start_web_preview_server(ws.root_path, req.target or "index.html", req.port or 5500, req.run_id or "")
    
    if req.run_id and res.get("success"):
        await emit(req.run_id, "server_started", "api", res)
        await emit(req.run_id, "preview_started", "api", res)
    return res

@router.post("/stop_server")
async def stop_server_endpoint(req: StopServerRequest):
    reg = get_process_registry()
    target_id = req.process_id or req.port or 5500
    res = reg.stop_process(target_id)
    if req.run_id:
        await emit(req.run_id, "server_stopped", "api", res)
        await emit(req.run_id, "preview_stopped", "api", res)
    return res

@router.get("/processes")
def get_processes():
    reg = get_process_registry()
    return {"processes": reg.list_processes()}

@router.get("/detect_app")
def detect_application():
    ws = get_workspace_manager()
    dir_res = ws.list_directory(".")
    if not dir_res.get("success"):
        return {"app_type": "UNKNOWN", "files": []}

    files = [e["name"] for e in dir_res.get("entries", []) if not e.get("is_directory")]
    
    html_files = [f for f in files if f.endswith(".html")]
    py_files = [f for f in files if f.endswith(".py")]
    java_files = [f for f in files if f.endswith(".java")]
    js_files = [f for f in files if f.endswith(".js")]
    css_files = [f for f in files if f.endswith(".css")]

    if html_files:
        main_html = "ecommerce.html" if "ecommerce.html" in html_files else ("college_dashboard.html" if "college_dashboard.html" in html_files else html_files[0])
        return {
            "app_type": "WEB_APP",
            "main_file": main_html,
            "html_files": html_files,
            "css_files": css_files,
            "js_files": js_files,
            "can_preview": True,
            "can_run": False
        }

    if java_files:
        return {
            "app_type": "JAVA_SOURCE",
            "main_file": java_files[0],
            "files": java_files,
            "can_preview": False,
            "can_run": True
        }

    if py_files:
        is_server_py = any(f in py_files for f in ["server.py", "app.py", "main.py"])
        return {
            "app_type": "PYTHON_APP" if is_server_py and "requirements.txt" in files else "PYTHON_SCRIPT",
            "main_file": py_files[0],
            "files": py_files,
            "can_preview": False,
            "can_run": True
        }

    if js_files:
        return {
            "app_type": "JS_SCRIPT",
            "main_file": js_files[0],
            "files": js_files,
            "can_preview": False,
            "can_run": True
        }

    return {
        "app_type": "STATIC_FILES",
        "main_file": files[0] if files else None,
        "files": files,
        "can_preview": False,
        "can_run": False
    }
