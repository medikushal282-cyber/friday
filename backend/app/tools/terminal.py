import subprocess
import threading
import uuid
import os
import psutil
from typing import Dict, List, Optional
from app.db.database import db

class TerminalSession:
    def __init__(self, t_id: str, command: str, cwd: str):
        self.t_id = t_id
        self.command = command
        self.cwd = cwd
        self.process: Optional[subprocess.Popen] = None
        self.logs = []
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        self.process = subprocess.Popen(
            self.command,
            cwd=self.cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        db.add_terminal(self.t_id, self.process.pid, self.command, self.cwd, "running")
        
        self.thread = threading.Thread(target=self._read_output, daemon=True)
        self.thread.start()

    def _read_output(self):
        try:
            for line in iter(self.process.stdout.readline, ''):
                if line:
                    with self.lock:
                        self.logs.append(line)
        except Exception:
            pass
        finally:
            self.process.wait()
            db.update_terminal_status(self.t_id, "stopped")

    def kill(self) -> bool:
        if self.process and self.process.poll() is None:
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                db.update_terminal_status(self.t_id, "killed")
                return True
            except Exception:
                return False
        return False

    def get_logs(self) -> str:
        with self.lock:
            return "".join(self.logs)


class TerminalManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TerminalManager, cls).__new__(cls)
            cls._instance.sessions = {}
        return cls._instance

    def spawn(self, command: str, cwd: str) -> str:
        t_id = str(uuid.uuid4())
        session = TerminalSession(t_id, command, cwd)
        self.sessions[t_id] = session
        session.start()
        return t_id

    def kill_terminal(self, t_id: str) -> bool:
        session = self.sessions.get(t_id)
        if session:
            return session.kill()
        return False

    def get_logs(self, t_id: str) -> Optional[str]:
        session = self.sessions.get(t_id)
        if session:
            return session.get_logs()
        return None

    def list_terminals(self) -> List[Dict]:
        return db.get_terminals()

def get_terminal_manager() -> TerminalManager:
    return TerminalManager()

# Tool wrapper for the agent
def run_background_command(command: str, cwd: str) -> Dict:
    mgr = get_terminal_manager()
    t_id = mgr.spawn(command, cwd)
    return {"success": True, "terminal_id": t_id, "message": f"Started background process {t_id}"}

def manage_background_terminal(terminal_id: str, action: str) -> Dict:
    mgr = get_terminal_manager()
    if action == "kill":
        success = mgr.kill_terminal(terminal_id)
        return {"success": success, "message": "Terminal killed" if success else "Failed to kill"}
    elif action == "logs":
        logs = mgr.get_logs(terminal_id)
        return {"success": logs is not None, "logs": logs[-2000:] if logs else "Terminal not found"}
    return {"success": False, "error": "Invalid action"}
