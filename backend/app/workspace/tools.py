import os
from typing import Dict, Any, Optional

from app.workspace.manager import get_workspace_manager, PathSecurityError, CommandDeniedError
from app.workspace.policy import check_command_policy, POLICY_SAFE, POLICY_APPROVAL_REQUIRED, POLICY_DENIED

TOOL_SCHEMAS = {
    "list_directory": {
        "description": "Lists contents of a directory in the workspace.",
        "parameters": {"path": "string (optional, defaults to '.')"}
    },
    "read_file": {
        "description": "Reads contents of a file inside the workspace.",
        "parameters": {"path": "string (required)"}
    },
    "create_file": {
        "description": "Creates a new file in the workspace with given content.",
        "parameters": {"path": "string (required)", "content": "string (required)"}
    },
    "update_file": {
        "description": "Updates an existing file in the workspace with given content.",
        "parameters": {"path": "string (required)", "content": "string (required)"}
    },
    "delete_file": {
        "description": "Deletes a file inside the workspace. Requires approval if protected or destructive.",
        "parameters": {"path": "string (required)"}
    },
    "run_command": {
        "description": "Executes a safe process inside the workspace with cwd = workspace_root.",
        "parameters": {"command": "string or list of strings (required)", "timeout": "integer (optional, default 30)"}
    },
    "inspect_runtime": {
        "description": "Returns runtime environment information for Python, Node, Git, etc.",
        "parameters": {}
    }
}

def tool_list_directory(path: str = ".") -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        res = ws.list_directory(path)
        return {
            "success": res.get("success", False),
            "tool": "list_directory",
            "path": res.get("path", path),
            "entries": res.get("entries", []),
            "error": res.get("error")
        }
    except Exception as e:
        return {"success": False, "tool": "list_directory", "path": path, "error": str(e)}

def tool_read_file(path: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        res = ws.read_file(path)
        return {
            "success": res.get("success", False),
            "tool": "read_file",
            "path": res.get("path", path),
            "content": res.get("content"),
            "error": res.get("error")
        }
    except Exception as e:
        return {"success": False, "tool": "read_file", "path": path, "error": str(e)}

def tool_create_file(path: str, content: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        # Check if file exists; if exists, report that it already exists
        full_path = ws.resolve_path(path)
        if os.path.exists(full_path):
            # If it exists, we still write but note it was existing or update
            pass
        res = ws.write_file(path, content)
        line_count = len(content.splitlines())
        return {
            "success": res.get("success", False),
            "tool": "create_file",
            "path": res.get("path", path),
            "lines": line_count,
            "bytes_written": res.get("bytes_written", 0),
            "error": res.get("error")
        }
    except Exception as e:
        return {"success": False, "tool": "create_file", "path": path, "error": str(e)}

def tool_update_file(path: str, content: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        full_path = ws.resolve_path(path)
        existed = os.path.exists(full_path)
        old_lines = 0
        if existed:
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    old_lines = len(f.readlines())
            except Exception:
                pass
                
        res = ws.write_file(path, content)
        new_lines = len(content.splitlines())
        diff_info = f"+{max(0, new_lines - old_lines)} / -{max(0, old_lines - new_lines)} lines"
        return {
            "success": res.get("success", False),
            "tool": "update_file",
            "path": res.get("path", path),
            "lines": new_lines,
            "diff": diff_info,
            "bytes_written": res.get("bytes_written", 0),
            "error": res.get("error")
        }
    except Exception as e:
        return {"success": False, "tool": "update_file", "path": path, "error": str(e)}

def tool_delete_file(path: str) -> Dict[str, Any]:
    # Destructive file deletions in this phase require explicit approval per security policy
    return {
        "success": False,
        "tool": "delete_file",
        "path": path,
        "status": "approval_required",
        "reason": "Destructive file deletion requires explicit user approval.",
        "policy": POLICY_APPROVAL_REQUIRED
    }

def tool_run_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        policy, reason = check_command_policy(command)
        if policy == POLICY_DENIED:
            return {
                "success": False,
                "tool": "run_command",
                "command": command,
                "status": "denied",
                "reason": reason,
                "exit_code": 126
            }
        elif policy == POLICY_APPROVAL_REQUIRED:
            return {
                "success": False,
                "tool": "run_command",
                "command": command,
                "status": "approval_required",
                "reason": reason,
                "exit_code": 126
            }

        res = ws.execute_process(command, timeout=timeout)
        return {
            "success": res.get("exit_code") == 0,
            "tool": "run_command",
            "command": res.get("command", command),
            "exit_code": res.get("exit_code", 1),
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "duration": res.get("duration", 0),
            "working_directory": res.get("working_directory")
        }
    except CommandDeniedError as e:
        return {
            "success": False,
            "tool": "run_command",
            "command": command,
            "status": "denied",
            "error": str(e),
            "exit_code": 126
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "run_command",
            "command": command,
            "error": str(e),
            "exit_code": 1
        }

def tool_inspect_runtime() -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        runtimes = ws.get_runtime_info()
        return {
            "success": True,
            "tool": "inspect_runtime",
            "runtime": runtimes
        }
    except Exception as e:
        return {"success": False, "tool": "inspect_runtime", "error": str(e)}

DISPATCH_TABLE = {
    "list_directory": tool_list_directory,
    "read_file": tool_read_file,
    "create_file": tool_create_file,
    "update_file": tool_update_file,
    "delete_file": tool_delete_file,
    "run_command": tool_run_command,
    "inspect_runtime": tool_inspect_runtime
}

def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    if tool_name not in DISPATCH_TABLE:
        return {
            "success": False,
            "tool": tool_name,
            "error": f"Unknown tool: {tool_name}"
        }
    fn = DISPATCH_TABLE[tool_name]
    try:
        return fn(**kwargs)
    except TypeError as e:
        return {
            "success": False,
            "tool": tool_name,
            "error": f"Invalid arguments for tool {tool_name}: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "tool": tool_name,
            "error": str(e)
        }
