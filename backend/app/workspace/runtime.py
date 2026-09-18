import os
import shutil
import subprocess
import sys
from typing import Dict, Any, Optional

def detect_python(workspace_root: str) -> Dict[str, Any]:
    # Priority 1: workspace .venv
    venv_candidates = [
        os.path.join(workspace_root, ".venv", "Scripts", "python.exe"),
        os.path.join(workspace_root, ".venv", "bin", "python"),
        os.path.join(workspace_root, "venv", "Scripts", "python.exe"),
        os.path.join(workspace_root, "venv", "bin", "python"),
    ]
    for venv_py in venv_candidates:
        if os.path.isfile(venv_py):
            try:
                res = subprocess.run(
                    [venv_py, "-c", "import sys; print(sys.executable); print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    lines = res.stdout.strip().splitlines()
                    if len(lines) >= 2:
                        return {
                            "available": True,
                            "executable": lines[0],
                            "version": lines[1],
                            "source": "venv"
                        }
            except Exception:
                pass

    # Priority 2: Windows py launcher
    py_launcher = shutil.which("py")
    if py_launcher:
        try:
            res = subprocess.run(
                [py_launcher, "-c", "import sys; print(sys.executable); print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if res.returncode == 0:
                lines = res.stdout.strip().splitlines()
                if len(lines) >= 2:
                    return {
                        "available": True,
                        "executable": lines[0],
                        "version": lines[1],
                        "source": "py_launcher"
                    }
        except Exception:
            pass

    # Priority 3 & 4: python, python3
    for cmd in ["python", "python3"]:
        target_cmd = shutil.which(cmd)
        if target_cmd:
            try:
                res = subprocess.run(
                    [target_cmd, "-c", "import sys; print(sys.executable); print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if res.returncode == 0:
                    lines = res.stdout.strip().splitlines()
                    if len(lines) >= 2:
                        return {
                            "available": True,
                            "executable": lines[0],
                            "version": lines[1],
                            "source": "system"
                        }
            except Exception:
                pass

    # Fallback: check current sys.executable if running inside valid python
    if sys.executable and os.path.isfile(sys.executable):
        return {
            "available": True,
            "executable": sys.executable,
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "source": "current_process"
        }

    return {
        "available": False,
        "executable": None,
        "version": None,
        "source": None
    }

def detect_cli_tool(name: str) -> Dict[str, Any]:
    tool_path = shutil.which(name)
    if not tool_path:
        return {
            "available": False,
            "version": None,
            "executable": None
        }
    try:
        res = subprocess.run(
            [tool_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            shell=True if os.name == "nt" and tool_path.endswith((".cmd", ".bat")) else False
        )
        version_str = res.stdout.strip() or res.stderr.strip()
        if version_str.lower().startswith("git version "):
            version_str = version_str[12:].strip()
        elif version_str.startswith("v"):
            version_str = version_str[1:]
        return {
            "available": res.returncode == 0,
            "version": version_str if res.returncode == 0 else None,
            "executable": tool_path
        }
    except Exception:
        return {
            "available": False,
            "version": None,
            "executable": tool_path
        }

def detect_all_runtimes(workspace_root: str) -> Dict[str, Any]:
    return {
        "python": detect_python(workspace_root),
        "node": detect_cli_tool("node"),
        "npm": detect_cli_tool("npm"),
        "pnpm": detect_cli_tool("pnpm"),
        "git": detect_cli_tool("git")
    }
