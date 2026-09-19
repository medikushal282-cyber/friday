from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class AgentProfile(BaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str]
    tools: List[str]
    approval_policy: str = "standard"
    default_model: Optional[str] = None

DEFAULT_AGENT_PROFILES: Dict[str, AgentProfile] = {
    "orchestrator": AgentProfile(
        id="orchestrator",
        name="Orchestrator",
        description="Analyzes objectives, constructs execution workflows, and coordinates specialized agents.",
        capabilities=["planning", "task_decomposition", "agent_selection", "coordination"],
        tools=["list_directory", "inspect_runtime"],
        approval_policy="standard"
    ),
    "researcher": AgentProfile(
        id="researcher",
        name="Research Agent",
        description="Investigates technical specifications, APIs, algorithms, and workspace context.",
        capabilities=["knowledge_retrieval", "spec_lookup", "context_analysis"],
        tools=["list_directory", "read_file"],
        approval_policy="standard"
    ),
    "coding_agent": AgentProfile(
        id="coding_agent",
        name="Python Coding Agent",
        description="Authors, modifies, and refactors application source code and scripts.",
        capabilities=["code_generation", "refactoring", "scripting", "file_crud"],
        tools=["read_file", "create_file", "update_file"],
        approval_policy="standard"
    ),
    "testing_agent": AgentProfile(
        id="testing_agent",
        name="Testing Agent",
        description="Executes programs, runs test suites, and verifies execution outputs and exit codes.",
        capabilities=["command_execution", "test_runner", "exit_code_validation"],
        tools=["run_command", "read_file", "inspect_runtime"],
        approval_policy="sensitive"
    ),
    "debugging_agent": AgentProfile(
        id="debugging_agent",
        name="Debugging Agent",
        description="Diagnoses tracebacks, syntax errors, and runtime crashes, generating corrective fixes.",
        capabilities=["traceback_analysis", "syntax_diagnosis", "artifact_repair"],
        tools=["read_file", "update_file", "run_command"],
        approval_policy="standard"
    ),
    "data_agent": AgentProfile(
        id="data_agent",
        name="Data Engineering Agent",
        description="Transforms structured data (CSV, JSON), generates data pipelines and reports.",
        capabilities=["data_transformation", "csv_processing", "json_serialization"],
        tools=["read_file", "create_file", "update_file", "run_command"],
        approval_policy="standard"
    ),
    "security_agent": AgentProfile(
        id="security_agent",
        name="Security Policy Agent",
        description="Enforces workspace boundary containment, reviews sensitive operations, and handles approvals.",
        capabilities=["policy_enforcement", "deletion_review", "path_containment"],
        tools=["delete_file"],
        approval_policy="strict"
    ),
    "review_agent": AgentProfile(
        id="review_agent",
        name="Review & Validation Agent",
        description="Inspects artifacts against user requirements and validates outcome fidelity.",
        capabilities=["code_review", "semantic_validation", "acceptance_checking"],
        tools=["read_file"],
        approval_policy="standard"
    )
}

class AgentRegistry:
    def __init__(self):
        self._profiles: Dict[str, AgentProfile] = dict(DEFAULT_AGENT_PROFILES)

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        return self._profiles.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [p.dict() for p in self._profiles.values()]

    def select_agents_for_objective(self, objective: str) -> List[str]:
        obj_lower = objective.lower()
        selected = ["orchestrator"]

        if any(k in obj_lower for k in ["research", "investigate", "look up", "how to", "docs"]):
            selected.append("researcher")

        if "csv" in obj_lower or "json" in obj_lower or "dataset" in obj_lower or "report" in obj_lower:
            selected.append("data_agent")

        if any(k in obj_lower for k in ["create", "modify", "update", "write", "build", "script", "program", ".py", ".html"]):
            selected.append("coding_agent")

        if any(k in obj_lower for k in ["run", "test", "verify", "execute", "calculate", "check"]):
            selected.append("testing_agent")

        if any(k in obj_lower for k in ["delete", "remove", "clean", "drop"]):
            selected.append("security_agent")

        selected.append("review_agent")
        return list(dict.fromkeys(selected))

_agent_registry = AgentRegistry()

def get_agent_registry() -> AgentRegistry:
    return _agent_registry
