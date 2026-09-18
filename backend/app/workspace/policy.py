import re
import shlex
from typing import Tuple, List, Union

POLICY_SAFE = "SAFE"
POLICY_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
POLICY_DENIED = "DENIED"

# Dangerous patterns that immediately deny execution
DENIED_PATTERNS = [
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breg\s+(add|delete)\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bpowershell(\.exe)?\s+(-enc|-encodedcommand)\b",
    r":\s*>\s*/dev/sd",
    r"[a-zA-Z]:\\Windows\\",
    r"/etc/shadow",
    r"/etc/passwd",
    r"\bcd\s+\.\.[\\/]\.\.",  # deep directory escape attempts
]

# Patterns requiring explicit user approval
APPROVAL_PATTERNS = [
    r"\bpip\s+install\b",
    r"\bnpm\s+(install|i|add)\b",
    r"\bpnpm\s+(install|i|add)\b",
    r"\byarn\s+add\b",
    r"\bdel\s+/[fFqQsS]\b",
    r"\brm\s+(-rf|-fr|-r)\b",
    r"\brmdir\s+/[sS]\b",
    r"\bgit\s+(push|reset\s+--hard|clean\s+-fd?)\b",
]

# Safe commands or prefix commands
SAFE_COMMAND_PREFIXES = [
    "python",
    "python3",
    "py",
    "node",
    "npm test",
    "npm run",
    "pnpm test",
    "pnpm run",
    "git status",
    "git diff",
    "git log",
    "git branch",
    "git show",
    "dir",
    "ls",
    "type",
    "cat",
    "echo",
    "pwd",
]

def check_command_policy(command: Union[str, List[str]]) -> Tuple[str, str]:
    cmd_str = " ".join(command) if isinstance(command, list) else command
    cmd_stripped = cmd_str.strip()
    cmd_lower = cmd_stripped.lower()

    # 1. Check DENIED patterns
    for pattern in DENIED_PATTERNS:
        if re.search(pattern, cmd_lower):
            return POLICY_DENIED, f"Command contains prohibited pattern: {pattern}"

    # 2. Check APPROVAL_REQUIRED patterns
    for pattern in APPROVAL_PATTERNS:
        if re.search(pattern, cmd_lower):
            return POLICY_APPROVAL_REQUIRED, f"Command requires approval: {pattern}"

    # 3. Check SAFE prefixes
    # Tokenize the start of the command
    for safe_prefix in SAFE_COMMAND_PREFIXES:
        if cmd_lower == safe_prefix or cmd_lower.startswith(safe_prefix + " "):
            return POLICY_SAFE, "Command is classified as safe"
    
    # Handle quoted absolute paths like '"C:\Program Files\Python313\python.exe" "script.py"'
    # shlex handles the quoted executable with spaces correctly
    try:
        tokens = shlex.split(cmd_str, posix=True)
        if tokens:
            first_token_lower = tokens[0].lower()
            if "python" in first_token_lower or first_token_lower == "py":
                return POLICY_SAFE, "Command is classified as safe (quoted python executable)"
    except Exception:
        pass
            
    # Also check if it is executing a python file or node script in workspace
    # Handle quoted paths like '"C:\Program Files\python.exe" "script.py"' (trailing quote breaks endswith)
    stripped_for_ext = cmd_lower.strip().rstrip('"').rstrip("'").strip()
    if stripped_for_ext.endswith(".py") or stripped_for_ext.endswith(".js") or stripped_for_ext.endswith(".ts"):
        return POLICY_SAFE, "Executing script"

    # Default to APPROVAL_REQUIRED for unknown/unclassified commands
    return POLICY_APPROVAL_REQUIRED, "Command is not on the safe whitelist"
