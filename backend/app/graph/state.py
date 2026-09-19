from typing import TypedDict, List, Dict, Any, Optional

class FraidayState(TypedDict):
    run_id: str
    objective: str

    workspace: Dict[str, Any]
    conversation_context: List[Dict[str, Any]]
    continuation_context: Optional[Dict[str, Any]]
    previous_run_id: Optional[str]
    continuation_mode: bool

    plan: List[Dict[str, Any]]
    current_step: str

    research: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    observations: List[Dict[str, Any]]
    artifacts: List[Dict[str, Any]]

    validation_results: List[Dict[str, Any]]

    status: str
    error: Optional[Any]

    retry_count: int
    max_retries: int
    recovery_history: List[Dict[str, Any]]
    knowledge_matches: List[Dict[str, Any]]
    knowledge_sources: List[Dict[str, Any]]
    recovery_mode: bool

    # Human-in-the-loop approval state
    approval_required: bool
    approval_status: str
    approval_request: Optional[Dict[str, Any]]
