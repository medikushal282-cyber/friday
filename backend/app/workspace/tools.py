import os
import asyncio
from typing import Dict, Any, Optional, Union, Tuple, List

from app.workspace.manager import get_workspace_manager, PathSecurityError, CommandDeniedError
from app.workspace.policy import check_command_policy, POLICY_SAFE, POLICY_APPROVAL_REQUIRED, POLICY_DENIED
from app.workspace.process_manager import (
    get_process_registry, classify_command, COMMAND_NORMAL, COMMAND_LONG_RUNNING, COMMAND_WEB_PREVIEW
)
from app.events import emit
from app.workspace.artifact_cleaner import extract_and_validate_artifact

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
    "start_server": {
        "description": "Launches a persistent web server or background process in non-blocking mode with startup verification.",
        "parameters": {"command": "string or list (optional)", "target": "string (optional)", "port": "integer (optional, default 5500)"}
    },
    "stop_server": {
        "description": "Stops a managed background process or preview server.",
        "parameters": {"process_id": "string (optional)", "port": "integer (optional)"}
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
        if not res.get("success"):
            err_msg = res.get("error", "Failed to list directory")
            code = "FILE_NOT_FOUND" if "does not exist" in err_msg else "TOOL_EXECUTION_ERROR"
            return {
                "success": False,
                "tool": "list_directory",
                "path": path,
                "result": None,
                "error": {"code": code, "message": err_msg}
            }
        result_payload = {
            "path": res.get("path", path),
            "entries": res.get("entries", [])
        }
        return {
            "success": True,
            "tool": "list_directory",
            "path": res.get("path", path),
            "entries": res.get("entries", []),
            "result": result_payload,
            "error": None
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "tool": "list_directory",
            "path": path,
            "result": None,
            "error": {"code": "PATH_SECURITY_ERROR", "message": str(e)}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "list_directory",
            "path": path,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_read_file(path: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        res = ws.read_file(path)
        if not res.get("success"):
            err_msg = res.get("error", "Failed to read file")
            code = "FILE_NOT_FOUND" if "does not exist" in err_msg else "TOOL_EXECUTION_ERROR"
            return {
                "success": False,
                "tool": "read_file",
                "path": path,
                "content": None,
                "result": None,
                "error": {"code": code, "message": err_msg}
            }
        content = res.get("content", "")
        result_payload = {
            "path": res.get("path", path),
            "content": content,
            "bytes_read": len(content.encode("utf-8"))
        }
        return {
            "success": True,
            "tool": "read_file",
            "path": res.get("path", path),
            "content": content,
            "result": result_payload,
            "error": None
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "tool": "read_file",
            "path": path,
            "result": None,
            "error": {"code": "PATH_SECURITY_ERROR", "message": str(e)}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "read_file",
            "path": path,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_create_file(path: str, content: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        valid, clean_content, err_msg = extract_and_validate_artifact(path, content)
        if not valid:
            return {
                "success": False,
                "tool": "create_file",
                "path": path,
                "result": None,
                "error": {"code": "ARTIFACT_EXTRACTION_ERROR", "message": err_msg or "Failed to extract valid artifact content"}
            }
        content = clean_content
        res = ws.write_file(path, content)
        if not res.get("success"):
            return {
                "success": False,
                "tool": "create_file",
                "path": path,
                "result": None,
                "error": {"code": "TOOL_EXECUTION_ERROR", "message": res.get("error", "Failed to create file")}
            }
        lines = len(content.splitlines())
        bytes_written = res.get("bytes_written", len(content.encode("utf-8")))
        result_payload = {
            "path": res.get("path", path),
            "lines": lines,
            "bytes_written": bytes_written
        }
        return {
            "success": True,
            "tool": "create_file",
            "path": res.get("path", path),
            "lines": lines,
            "bytes_written": bytes_written,
            "result": result_payload,
            "error": None
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "tool": "create_file",
            "path": path,
            "result": None,
            "error": {"code": "PATH_SECURITY_ERROR", "message": str(e)}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "create_file",
            "path": path,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_update_file(path: str, content: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        valid, clean_content, err_msg = extract_and_validate_artifact(path, content)
        if not valid:
            return {
                "success": False,
                "tool": "update_file",
                "path": path,
                "result": None,
                "error": {"code": "ARTIFACT_EXTRACTION_ERROR", "message": err_msg or "Failed to extract valid artifact content"}
            }
        content = clean_content
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
        if not res.get("success"):
            return {
                "success": False,
                "tool": "update_file",
                "path": path,
                "result": None,
                "error": {"code": "TOOL_EXECUTION_ERROR", "message": res.get("error", "Failed to update file")}
            }
        new_lines = len(content.splitlines())
        diff_info = f"+{max(0, new_lines - old_lines)} / -{max(0, old_lines - new_lines)} lines"
        bytes_written = res.get("bytes_written", len(content.encode("utf-8")))
        result_payload = {
            "path": res.get("path", path),
            "lines": new_lines,
            "diff": diff_info,
            "bytes_written": bytes_written
        }
        return {
            "success": True,
            "tool": "update_file",
            "path": res.get("path", path),
            "lines": new_lines,
            "diff": diff_info,
            "bytes_written": bytes_written,
            "result": result_payload,
            "error": None
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "tool": "update_file",
            "path": path,
            "result": None,
            "error": {"code": "PATH_SECURITY_ERROR", "message": str(e)}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "update_file",
            "path": path,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_delete_file(path: str) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        # Validate path containment first
        full_path = ws.resolve_path(path)
        reason = "Destructive file deletion requires explicit user approval."
        return {
            "success": False,
            "tool": "delete_file",
            "path": path,
            "status": "approval_required",
            "reason": reason,
            "policy": POLICY_APPROVAL_REQUIRED,
            "result": {
                "status": "approval_required",
                "reason": reason,
                "policy": POLICY_APPROVAL_REQUIRED
            },
            "error": {
                "code": "APPROVAL_REQUIRED",
                "message": reason
            }
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "tool": "delete_file",
            "path": path,
            "result": None,
            "error": {"code": "PATH_SECURITY_ERROR", "message": str(e)}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "delete_file",
            "path": path,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_start_server(
    command: Optional[Union[str, List[str]]] = None,
    target: str = "index.html",
    port: int = 5500,
    run_id: str = ""
) -> Dict[str, Any]:
    ws = get_workspace_manager()
    reg = get_process_registry()
    try:
        cmd_kind = classify_command(command or "", action="START_SERVER") if command else COMMAND_WEB_PREVIEW

        if cmd_kind == COMMAND_WEB_PREVIEW or not command:
            res = reg.start_web_preview_server(
                workspace_root=ws.root_path,
                target_file=target,
                preferred_port=port,
                run_id=run_id
            )
        else:
            res = reg.start_long_running_process(
                command=command,
                cwd=ws.root_path,
                port=port,
                run_id=run_id
            )

        if not res.get("success"):
            return {
                "success": False,
                "tool": "start_server",
                "command": str(command or f"python -m http.server {port}"),
                "status": "failed",
                "exit_code": 1,
                "error": {"code": "SERVER_START_ERROR", "message": res.get("error", "Failed to start server")}
            }

        url = res.get("url") or f"http://localhost:{res.get('port', port)}/{target.lstrip('/')}"
        result_payload = {
            "status": "server_started",
            "command": res.get("command"),
            "port": res.get("port"),
            "pid": res.get("pid"),
            "url": url,
            "reused": res.get("reused", False)
        }
        return {
            "success": True,
            "tool": "start_server",
            "command": res.get("command"),
            "exit_code": 0,
            "stdout": f"Server started successfully at {url} (PID {res.get('pid')})",
            "stderr": "",
            "duration": 0.5,
            "status": "server_started",
            "url": url,
            "port": res.get("port"),
            "pid": res.get("pid"),
            "result": result_payload,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "start_server",
            "exit_code": 1,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_stop_server(process_id: Optional[str] = None, port: Optional[int] = None) -> Dict[str, Any]:
    reg = get_process_registry()
    try:
        target_id = process_id or port or 5500
        res = reg.stop_process(target_id)
        return {
            "success": res.get("success", False),
            "tool": "stop_server",
            "status": "stopped",
            "result": res,
            "error": None if res.get("success") else {"code": "STOP_SERVER_ERROR", "message": res.get("error")}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "stop_server",
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_run_command(command: Union[str, List[str]], timeout: int = 30) -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        policy, reason = check_command_policy(command)
        if policy == POLICY_DENIED:
            return {
                "success": False,
                "tool": "run_command",
                "command": str(command),
                "status": "denied",
                "reason": reason,
                "exit_code": 126,
                "result": None,
                "error": {
                    "code": "COMMAND_DENIED",
                    "message": f"Command execution denied by security policy: {reason}"
                }
            }
        elif policy == POLICY_APPROVAL_REQUIRED:
            return {
                "success": False,
                "tool": "run_command",
                "command": str(command),
                "status": "approval_required",
                "reason": reason,
                "exit_code": 126,
                "result": {
                    "status": "approval_required",
                    "reason": reason
                },
                "error": {
                    "code": "APPROVAL_REQUIRED",
                    "message": f"Command requires approval: {reason}"
                }
            }

        # --- NON-BLOCKING AUTOMATIC CLASSIFICATION FOR SERVERS ---
        cmd_kind = classify_command(command)
        if cmd_kind in [COMMAND_WEB_PREVIEW, COMMAND_LONG_RUNNING]:
            # Automatically route long-running server command through tool_start_server to avoid hanging wait()
            return tool_start_server(command=command)

        res = ws.execute_process(command, timeout=timeout)
        success = (res.get("exit_code") == 0)
        result_payload = {
            "command": res.get("command", str(command)),
            "exit_code": res.get("exit_code", 1),
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "duration": res.get("duration", 0),
            "working_directory": res.get("working_directory")
        }
        
        error_info = None
        if not success:
            err_msg = res.get("stderr", "").strip() or f"Process exited with code {res.get('exit_code')}"
            error_info = {
                "code": "PROCESS_EXECUTION_ERROR",
                "message": err_msg
            }

        return {
            "success": success,
            "tool": "run_command",
            "command": res.get("command", str(command)),
            "exit_code": res.get("exit_code", 1),
            "stdout": res.get("stdout", ""),
            "stderr": res.get("stderr", ""),
            "duration": res.get("duration", 0),
            "working_directory": res.get("working_directory"),
            "result": result_payload,
            "error": error_info
        }
    except CommandDeniedError as e:
        return {
            "success": False,
            "tool": "run_command",
            "command": str(command),
            "status": "denied",
            "exit_code": 126,
            "result": None,
            "error": {"code": "COMMAND_DENIED", "message": str(e)}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "run_command",
            "command": str(command),
            "exit_code": 1,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def tool_inspect_runtime() -> Dict[str, Any]:
    ws = get_workspace_manager()
    try:
        runtimes = ws.get_runtime_info()
        return {
            "success": True,
            "tool": "inspect_runtime",
            "runtime": runtimes,
            "result": {"runtime": runtimes},
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "tool": "inspect_runtime",
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

DISPATCH_TABLE = {
    "list_directory": tool_list_directory,
    "read_file": tool_read_file,
    "create_file": tool_create_file,
    "update_file": tool_update_file,
    "delete_file": tool_delete_file,
    "run_command": tool_run_command,
    "start_server": tool_start_server,
    "stop_server": tool_stop_server,
    "inspect_runtime": tool_inspect_runtime
}

def validate_action_schema(action: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
    if not isinstance(action, dict):
        return False, {"code": "INVALID_ACTION_FORMAT", "message": "Action must be a JSON object"}
    
    tool_name = action.get("tool")
    if not tool_name or not isinstance(tool_name, str):
        return False, {"code": "INVALID_ACTION_FORMAT", "message": "Action missing required 'tool' field"}
        
    if tool_name not in TOOL_SCHEMAS:
        return False, {"code": "UNKNOWN_TOOL", "message": f"Tool '{tool_name}' is not recognized"}
        
    args = action.get("arguments")
    if args is None:
        args = {}
    elif not isinstance(args, dict):
        return False, {"code": "INVALID_ARGUMENTS", "message": "Action 'arguments' must be a JSON object"}
        
    if tool_name in ["read_file", "delete_file"]:
        if "path" not in args or not str(args["path"]).strip():
            return False, {"code": "INVALID_ARGUMENTS", "message": f"Tool '{tool_name}' requires non-empty 'path' argument"}
    elif tool_name in ["create_file", "update_file"]:
        if "path" not in args or not str(args["path"]).strip():
            return False, {"code": "INVALID_ARGUMENTS", "message": f"Tool '{tool_name}' requires non-empty 'path' argument"}
        if "content" not in args or args["content"] is None:
            return False, {"code": "INVALID_ARGUMENTS", "message": f"Tool '{tool_name}' requires 'content' argument"}
    elif tool_name == "run_command":
        if "command" not in args or not args["command"]:
            return False, {"code": "INVALID_ARGUMENTS", "message": "Tool 'run_command' requires 'command' argument"}

    return True, None

def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and executes a structured action:
    {
      "tool": "create_file",
      "arguments": {
        "path": "example.py",
        "content": "..."
      }
    }
    Returns a structured result.
    """
    valid, err = validate_action_schema(action)
    tool_name = action.get("tool", "unknown") if isinstance(action, dict) else "unknown"
    if not valid:
        return {
            "success": False,
            "tool": tool_name,
            "result": None,
            "error": err
        }
        
    args = action.get("arguments", {})
    fn = DISPATCH_TABLE[tool_name]
    try:
        return fn(**args)
    except TypeError as e:
        return {
            "success": False,
            "tool": tool_name,
            "result": None,
            "error": {"code": "INVALID_ARGUMENTS", "message": f"Invalid arguments for tool '{tool_name}': {e}"}
        }
    except Exception as e:
        return {
            "success": False,
            "tool": tool_name,
            "result": None,
            "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(e)}
        }

def execute_tool(tool: Union[str, Dict[str, Any]], **kwargs) -> Dict[str, Any]:
    """
    Flexible wrapper that handles both structured action dicts and traditional tool name + kwargs.
    """
    if isinstance(tool, dict):
        return execute_action(tool)
    else:
        return execute_action({"tool": tool, "arguments": kwargs})

def validate_python_source(rel_path: str) -> Dict[str, Any]:
    """
    Generic pre-execution artifact validator for Python source files.
    Verifies that target file exists inside workspace and is syntactically valid Python.
    Does NOT hardcode any specific filenames.
    """
    ws = get_workspace_manager()
    try:
        full_path = ws.resolve_path(rel_path)
    except PathSecurityError as e:
        return {
            "valid": False,
            "kind": "permission_error",
            "path": rel_path,
            "message": str(e)
        }

    if not os.path.exists(full_path):
        return {
            "valid": False,
            "kind": "missing_file",
            "path": rel_path,
            "message": f"File '{rel_path}' does not exist."
        }

    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        from app.workspace.artifact_cleaner import extract_and_validate_artifact
        valid, clean_content, err_msg = extract_and_validate_artifact(rel_path, content)
        if not valid:
            return {
                "valid": False,
                "kind": "syntax_error",
                "path": rel_path,
                "message": err_msg or "Artifact structure validation failed.",
                "stderr": f"Artifact validation failed for {rel_path}: {err_msg}"
            }

        conversational_prefixes = (
            "i'll start by", "i'll", "i will", "let me", "first, i'll", "first,",
            "now i need to", "now i", "insight", "here is the corrected code",
            "here is the python code", "here is", "here's", "sure,", "sure",
            "let's", "to accomplish this", "to solve", "this script", "the following",
            "below is", "certainly", "i need", "i cannot"
        )
        for line in content.splitlines():
            stripped = line.strip().lower()
            if any(stripped.startswith(p) for p in conversational_prefixes):
                if not line.strip().startswith("#") and not line.strip().startswith("import ") and not line.strip().startswith("from "):
                    return {
                        "valid": False,
                        "kind": "syntax_error",
                        "path": rel_path,
                        "message": f"Python artifact contains model preamble text: '{line.strip()[:60]}'",
                        "stderr": f"SyntaxError: Invalid model preamble line in {rel_path}: '{line.strip()[:60]}'"
                    }

        compile(clean_content, rel_path, "exec")
        return {
            "valid": True,
            "kind": "syntax_ok",
            "path": rel_path,
            "message": "Python syntax validation passed."
        }
    except SyntaxError as e:
        return {
            "valid": False,
            "kind": "syntax_error",
            "path": rel_path,
            "line": getattr(e, "lineno", 1),
            "message": f"SyntaxError: {e.msg} (line {getattr(e, 'lineno', 1)})",
            "stderr": f"SyntaxError: {e.msg} (line {getattr(e, 'lineno', 1)})\n  {getattr(e, 'text', '') or ''}"
        }
    except Exception as e:
        return {
            "valid": False,
            "kind": "syntax_error",
            "path": rel_path,
            "message": f"Compilation error: {str(e)}",
            "stderr": str(e)
        }

def classify_failure(exit_code: int, stdout: str = "", stderr: str = "", obj_reason: str = "") -> str:
    """
    Classifies process or validation failures into distinct categories:
    - syntax_error
    - runtime_error
    - missing_file
    - missing_arguments
    - permission_error
    - validation_error
    - command_error
    - artifact_extraction_error
    """
    if exit_code == 0 and not obj_reason:
        return "syntax_ok"

    combined = (stderr + "\n" + stdout + "\n" + obj_reason).lower()

    if any(err in combined for err in ["syntaxerror", "indentationerror", "taberror", "invalid syntax", "compilation error", "artifact_extraction_error", "extracted content for"]):
        return "syntax_error"

    if any(err in combined for err in ["nameerror", "typeerror", "valueerror", "attributeerror", "keyerror", "indexerror", "unboundlocalerror", "runtimeerror", "importerror", "modulenotfounderror", "zerodivisionerror", "recursionerror", "assertionerror"]):
        return "runtime_error"

    if "filenotfounderror" in combined or "no such file or directory" in combined or "does not exist" in combined:
        return "missing_file"

    if "usage:" in combined or "required positional argument" in combined or "too few arguments" in combined or "argparse" in combined or "sys.argv" in combined or "missing required input arguments" in combined:
        return "missing_arguments"

    if "permissionerror" in combined or "access denied" in combined or "permission denied" in combined or "path_security_error" in combined:
        return "permission_error"

    if "no execution observation" in combined or "missing target" in combined or "incomplete plan" in combined:
        return "plan_error"

    if "failed objective requirement validation" in combined or "missing expected text" in combined:
        return "validation_error"

    return "command_error"


