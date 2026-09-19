import os
import re
import time
import socket
import threading
import subprocess
import urllib.request
from typing import Dict, Any, List, Optional, Union

from app.workspace.web_server import get_web_server_manager
from app.workspace.policy import check_command_policy, POLICY_DENIED, POLICY_APPROVAL_REQUIRED

COMMAND_NORMAL = "NORMAL_COMMAND"
COMMAND_LONG_RUNNING = "LONG_RUNNING_PROCESS"
COMMAND_WEB_PREVIEW = "WEB_PREVIEW_SERVER"

def classify_command(command: Union[str, List[str]], action: str = "") -> str:
    """
    Classifies a command/action into:
    - COMMAND_WEB_PREVIEW: Static HTTP web servers (e.g., python -m http.server 5500, live-server, START_SERVER)
    - COMMAND_LONG_RUNNING: Persistent application processes (e.g., node server.js, uvicorn, npm run dev)
    - COMMAND_NORMAL: Standard synchronous processes (e.g., python script.py, pytest, git status)
    """
    if action and action.upper() in ["START_SERVER", "WEB_PREVIEW_SERVER", "PREVIEW"]:
        return COMMAND_WEB_PREVIEW

    cmd_str = " ".join(command) if isinstance(command, list) else str(command)
    cmd_lower = cmd_str.lower().strip()

    # Static Web Preview Server patterns
    if any(p in cmd_lower for p in [
        "http.server", "live-server", "http-server", "serve "
    ]) or cmd_lower.startswith("serve"):
        return COMMAND_WEB_PREVIEW

    # Persistent long-running application patterns
    if any(p in cmd_lower for p in [
        "uvicorn", "gunicorn", "flask run", "django runserver",
        "npm run dev", "npm start", "yarn dev", "yarn start", "pnpm dev",
        "vite", "next dev", "node server.js", "node app.js", "node index.js",
        "python app.py", "python server.py"
    ]) and not ("test" in cmd_lower or "pytest" in cmd_lower):
        # Exception: python app.py is only long running if app/server pattern is explicitly present
        if "node server" in cmd_lower or "node app" in cmd_lower or "uvicorn" in cmd_lower or "npm " in cmd_lower:
            return COMMAND_LONG_RUNNING

    return COMMAND_NORMAL

class ManagedProcessRegistry:
    def __init__(self):
        self._processes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def start_web_preview_server(
        self,
        workspace_root: str,
        target_file: str = "index.html",
        preferred_port: int = 5500,
        run_id: str = "",
        conversation_id: str = ""
    ) -> Dict[str, Any]:
        """
        Starts or reuses a thread-safe static WebServerManager preview instance.
        Verifies HTTP health with a bounded timeout and registers the process.
        """
        with self._lock:
            server_mgr = get_web_server_manager()
            res = server_mgr.start(workspace_root, preferred_port=preferred_port)

            if not res.get("success"):
                return {
                    "success": False,
                    "status": "failed",
                    "error": res.get("error", "Failed to start web preview server")
                }

            port = res["port"]
            rel_target = target_file.lstrip("/\\") if target_file else "index.html"
            url = f"http://localhost:{port}/{rel_target}"
            process_id = f"proc_web_{port}"

            # Check if already registered and active
            if process_id in self._processes and self._processes[process_id].get("status") == "RUNNING":
                proc_info = self._processes[process_id].copy()
                proc_info["url"] = url
                proc_info["reused"] = True
                proc_info["success"] = True
                return proc_info

            # Bounded HTTP health check (up to 3 seconds)
            health_ok = False
            start_check = time.time()
            check_url = f"http://127.0.0.1:{port}/"
            while time.time() - start_check < 3.0:
                try:
                    req = urllib.request.Request(check_url, method="HEAD")
                    with urllib.request.urlopen(req, timeout=1.0) as resp:
                        if resp.status < 500:
                            health_ok = True
                            break
                except Exception:
                    time.sleep(0.2)

            proc_record = {
                "process_id": process_id,
                "pid": os.getpid(),
                "command": f"python -m http.server {port}",
                "cwd": workspace_root,
                "port": port,
                "target_file": rel_target,
                "url": url,
                "process_type": COMMAND_WEB_PREVIEW,
                "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "status": "RUNNING",
                "health": "healthy" if health_ok else "unresponsive",
                "run_id": run_id,
                "conversation_id": conversation_id,
                "handle_type": "web_server_manager"
            }
            self._processes[process_id] = proc_record

            result_payload = proc_record.copy()
            result_payload["success"] = True
            return result_payload

    def start_long_running_process(
        self,
        command: Union[str, List[str]],
        cwd: str,
        port: Optional[int] = None,
        run_id: str = "",
        conversation_id: str = "",
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        Launches a non-blocking long-running background process (e.g. node server.js).
        Verifies process health for `timeout` seconds before returning.
        """
        policy, reason = check_command_policy(command)
        if policy == POLICY_DENIED:
            return {
                "success": False,
                "status": "denied",
                "error": f"Command denied by policy: {reason}"
            }
        elif policy == POLICY_APPROVAL_REQUIRED:
            return {
                "success": False,
                "status": "approval_required",
                "error": f"Command requires approval: {reason}"
            }

        cmd_repr = " ".join(command) if isinstance(command, list) else str(command)

        # Detect port from command string if not explicitly passed
        if port is None:
            m = re.search(r'\b(?:port|p|-p|=|:)?\s*([5-9]\d{3}|[1-4]\d{4})\b', cmd_repr, re.IGNORECASE)
            if m:
                try:
                    port = int(m.group(1))
                except ValueError:
                    port = None

        with self._lock:
            # Check for duplicate running command in same cwd
            for p_id, p_rec in self._processes.items():
                if p_rec.get("command") == cmd_repr and p_rec.get("cwd") == cwd and p_rec.get("status") == "RUNNING":
                    proc_handle = p_rec.get("_proc_handle")
                    if proc_handle and proc_handle.poll() is None:
                        res = p_rec.copy()
                        res.pop("_proc_handle", None)
                        res["reused"] = True
                        res["success"] = True
                        return res

            try:
                proc = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=isinstance(command, str)
                )

                # Bounded startup check (wait up to `timeout` seconds)
                start_time = time.time()
                early_exit = False
                exit_code = None

                while time.time() - start_time < min(timeout, 3.0):
                    ret = proc.poll()
                    if ret is not None:
                        early_exit = True
                        exit_code = ret
                        break
                    time.sleep(0.2)

                if early_exit and exit_code != 0:
                    stderr_content = ""
                    try:
                        _, stderr_content = proc.communicate(timeout=1.0)
                    except Exception:
                        pass
                    return {
                        "success": False,
                        "status": "failed",
                        "exit_code": exit_code,
                        "error": stderr_content.strip() or f"Process exited early with code {exit_code}"
                    }

                # Port connection check if port is specified
                health_ok = True
                if port:
                    health_ok = False
                    check_start = time.time()
                    while time.time() - check_start < max(1.0, timeout - 2.0):
                        try:
                            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                                health_ok = True
                                break
                        except Exception:
                            time.sleep(0.2)

                process_id = f"proc_{proc.pid}"
                proc_record = {
                    "process_id": process_id,
                    "pid": proc.pid,
                    "command": cmd_repr,
                    "cwd": cwd,
                    "port": port,
                    "url": f"http://localhost:{port}" if port else None,
                    "process_type": COMMAND_LONG_RUNNING,
                    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "status": "RUNNING",
                    "health": "healthy" if health_ok else "running",
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "_proc_handle": proc,
                    "handle_type": "popen"
                }
                self._processes[process_id] = proc_record

                res = proc_record.copy()
                res.pop("_proc_handle", None)
                res["success"] = True
                return res

            except Exception as e:
                return {
                    "success": False,
                    "status": "failed",
                    "error": f"Failed to launch process: {e}"
                }

    def stop_process(self, process_id_or_port: Union[str, int]) -> Dict[str, Any]:
        """Stops a managed process by process_id or port."""
        with self._lock:
            target_key = None
            for p_id, p_rec in self._processes.items():
                if p_id == str(process_id_or_port) or str(p_rec.get("port")) == str(process_id_or_port):
                    target_key = p_id
                    break

            if not target_key or target_key not in self._processes:
                # If static WebServerManager is running on that port, attempt to stop it
                if isinstance(process_id_or_port, int) or str(process_id_or_port).isdigit():
                    stop_res = get_web_server_manager().stop()
                    return {"success": True, "status": "stopped", "previous_port": process_id_or_port}
                return {"success": False, "error": f"Managed process '{process_id_or_port}' not found."}

            record = self._processes[target_key]
            handle_type = record.get("handle_type")

            if handle_type == "web_server_manager":
                get_web_server_manager().stop()
            elif handle_type == "popen":
                proc = record.get("_proc_handle")
                if proc and proc.poll() is None:
                    try:
                        proc.terminate()
                        proc.wait(timeout=2.0)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass

            record["status"] = "STOPPED"
            record["stopped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            
            res = record.copy()
            res.pop("_proc_handle", None)
            res["success"] = True
            return res

    def list_processes(self) -> List[Dict[str, Any]]:
        """Returns a list of all active managed processes."""
        with self._lock:
            active = []
            for p_id, rec in list(self._processes.items()):
                # Clean up exited Popen handles
                if rec.get("handle_type") == "popen":
                    proc = rec.get("_proc_handle")
                    if proc and proc.poll() is not None and rec["status"] == "RUNNING":
                        rec["status"] = "STOPPED"
                        rec["exit_code"] = proc.poll()
                clean_rec = rec.copy()
                clean_rec.pop("_proc_handle", None)
                active.append(clean_rec)
            return active

    def get_process(self, process_id_or_port: Union[str, int]) -> Optional[Dict[str, Any]]:
        with self._lock:
            for p_id, rec in self._processes.items():
                if p_id == str(process_id_or_port) or str(rec.get("port")) == str(process_id_or_port):
                    clean_rec = rec.copy()
                    clean_rec.pop("_proc_handle", None)
                    return clean_rec
            return None

# Singleton instance
_process_registry = ManagedProcessRegistry()

def get_process_registry() -> ManagedProcessRegistry:
    return _process_registry
