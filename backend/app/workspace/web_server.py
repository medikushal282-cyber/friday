import os
import socket
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Any, Optional

class WorkspaceHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging to stdout
        pass

class WebServerManager:
    def __init__(self):
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._port: Optional[int] = None
        self._workspace_root: Optional[str] = None
        self._status: str = "stopped"
        self._lock = threading.Lock()

    def _find_available_port(self, start_port: int = 5500, max_port: int = 5599) -> int:
        for port in range(start_port, max_port + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        return start_port

    def start(self, workspace_root: str, preferred_port: int = 5500) -> Dict[str, Any]:
        with self._lock:
            if self._server and self._status == "running":
                return {
                    "success": True,
                    "status": "running",
                    "port": self._port,
                    "url": f"http://localhost:{self._port}",
                    "workspace_root": self._workspace_root
                }

            if not os.path.exists(workspace_root):
                return {
                    "success": False,
                    "error": f"Workspace directory '{workspace_root}' does not exist."
                }

            port = self._find_available_port(preferred_port)

            class CustomHandler(WorkspaceHTTPRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, directory=workspace_root, **kwargs)

            try:
                server = HTTPServer(("127.0.0.1", port), CustomHandler)
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()

                self._server = server
                self._thread = thread
                self._port = port
                self._workspace_root = workspace_root
                self._status = "running"

                return {
                    "success": True,
                    "status": "running",
                    "port": port,
                    "url": f"http://localhost:{port}",
                    "workspace_root": workspace_root
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Failed to start static server: {e}"
                }

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if self._server:
                try:
                    self._server.shutdown()
                    self._server.server_close()
                except Exception:
                    pass
                self._server = None
                self._thread = None
                old_port = self._port
                self._port = None
                self._status = "stopped"
                return {
                    "success": True,
                    "status": "stopped",
                    "previous_port": old_port
                }
            return {
                "success": True,
                "status": "stopped"
            }

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "port": self._port,
                "url": f"http://localhost:{self._port}" if self._port else None,
                "workspace_root": self._workspace_root
            }

# Singleton instance
_web_server_manager = WebServerManager()

def get_web_server_manager() -> WebServerManager:
    return _web_server_manager
