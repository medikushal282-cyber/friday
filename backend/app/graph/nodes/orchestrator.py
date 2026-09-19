import json

from app.events import emit
from app.llm.router import call_groq


def clean_json(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


import re as _re

_CONVERSATIONAL_PATTERNS = (
    r"^\s*(hi|hello|hey|hiya|howdy|greetings)[\s!?.]*$",
    r"^\s*(thanks|thank you|thx|ty)[\s!?.]*$",
    r"^\s*good\s+(morning|afternoon|evening|night)[\s!?.]*$",
    r"^\s*what'?s\s+up[\s!?.]*$",
    r"^\s*how\s+are\s+you[\s!?.]*$",
    r"^\s*howdy[\s!?.]*$",
)

def _is_short_conversation(value: str) -> bool:
    v = value.strip().lower()
    if not v:
        return True
    # Very short inputs (<30 chars) with no action/research keywords are conversational
    if len(v) <= 30:
        for pat in _CONVERSATIONAL_PATTERNS:
            if _re.match(pat, v, _re.I):
                return True
        # Single/two-word greeting-like inputs without verbs
        tokens = _re.findall(r"[a-z]+", v)
        if len(tokens) <= 3 and not any(
            kw in v for kw in (
                "create", "write", "build", "generate", "make", "implement",
                "modify", "update", "change", "edit", "fix", "delete", "remove",
                "read", "show", "display", "inside", "inspect", "run", "execute",
                "test", "find", "research", "explain", "what is", "latest",
            )
        ):
            # Pure greeting/thanks without actionable intent
            if tokens and tokens[0] in {"hi","hello","hey","hiya","howdy","thanks","thank","greetings","good","whats","what","how"}:
                return True
    return False

def _groq_classify_intent(objective: str) -> str | None:
    """Ask Groq to classify intent into 8 categories. Returns None on failure."""
    try:
        from app.llm.router import call_groq as _call
        import json as _json
        system = (
            "You are an intent classifier for Fraiday workspace agent. "
            "Classify the user objective into exactly one of: "
            "conversation, research, create, modify, read, execute, delete, mixed. "
            "Definitions: conversation=greeting/thanks/smalltalk with no file/task request; "
            "research=asking to find/explain information; create=asking to create/write/build a file; "
            "modify=update/change existing file; read=show/read/display file content; "
            "execute=run/test a program; delete=remove a file; mixed=multiple or unclear intents. "
            "Return ONLY valid JSON: {\"intent\":\"conversation\"}"
        )
        raw = _call(system, f"Objective: {objective}")
        # Strip markdown fences
        txt = raw.strip()
        if txt.startswith("```"):
            txt = _re.sub(r"^```(?:json)?\s*", "", txt)
            txt = _re.sub(r"\s*```$", "", txt)
        data = _json.loads(txt.strip())
        intent = str(data.get("intent", "")).strip().lower()
        if intent in {"conversation","research","create","modify","read","execute","delete","mixed"}:
            return intent
    except Exception:
        pass
    return None

def detect_objective_type(objective: str) -> str:
    value = objective.lower().strip()

    # 1. Fast deterministic conversational gating (no LLM cost for obvious greetings)
    if _is_short_conversation(value):
        return "conversation"

    # 2. Groq-powered classification (compatible with existing Groq architecture)
    groq_intent = _groq_classify_intent(objective)
    if groq_intent:
        return groq_intent

    # 3. Deterministic fallback (preserves existing behavior)
    research_phrases = (
        "find",
        "research",
        "look up",
        "what is",
        "what are",
        "explain",
        "latest",
        "current",
        "documentation",
        "compare",
        "tell me about",
    )

    delete_phrases = (
        "delete",
        "remove",
        "erase",
    )

    modify_phrases = (
        "modify",
        "update",
        "change",
        "edit",
        "fix",
    )

    read_phrases = (
        "show me",
        "read",
        "display",
        "what is inside",
        "inspect",
    )

    create_phrases = (
        "create",
        "write",
        "build",
        "generate",
        "make a",
        "implement",
    )

    execute_phrases = (
        "run",
        "execute",
        "test",
    )

    if any(phrase in value for phrase in delete_phrases):
        return "delete"

    if any(phrase in value for phrase in modify_phrases):
        return "modify"

    if any(phrase in value for phrase in read_phrases):
        return "read"

    if any(phrase in value for phrase in create_phrases):
        return "create"

    if any(phrase in value for phrase in execute_phrases):
        return "execute"

    if any(phrase in value for phrase in research_phrases):
        return "research"

    return "mixed"


async def orchestrator_node(state):
    run_id = state["run_id"]
    objective = state["objective"]

    objective_type = detect_objective_type(objective)
    state["objective_type"] = objective_type

    await emit(
        run_id,
        "agent_thinking",
        "orchestrator",
        {
            "summary": f"Classifying objective as {objective_type}."
        },
    )

    # ------------------------------------------------------------
    # Pure research objectives should not create files or execute
    # arbitrary workspace actions.
    # ------------------------------------------------------------

    if objective_type == "research":
        steps = [
            {
                "id": "step_1",
                "agent": "researcher",
                "action": "acquire_knowledge",
                "description": "Search stored knowledge and acquire missing external information.",
                "status": "pending",
            },
            {
                "id": "step_2",
                "agent": "validator",
                "action": "validate_research",
                "description": "Validate that useful research findings were acquired.",
                "status": "pending",
            },
        ]

        state["plan"] = steps

        await emit(
            run_id,
            "plan_created",
            "orchestrator",
            {
                "steps": steps,
                "objective_type": objective_type,
            },
        )

        state["current_step"] = "researcher"
        return state

    # ------------------------------------------------------------
    # Conversational intent: no workspace mutation
    # ------------------------------------------------------------
    if objective_type == "conversation":
        # Generate friendly conversational reply (Groq if available, fallback otherwise)
        try:
            reply = await __import__("asyncio").to_thread(
                call_groq,
                "You are Fraiday, a friendly workspace assistant. Respond conversationally to greetings/thanks. Do NOT attempt to create, read, or execute files. Keep it short and helpful.",
                objective,
            )
        except Exception:
            # Deterministic fallback for offline / API failure (ASCII only for Windows console safety)
            low = objective.strip().lower()
            if low in {"hi", "hello", "hey", "hiya", "howdy", "greetings"} or low.startswith("hi "):
                reply = "Hi there! I'm Fraiday - your autonomous workspace assistant. How can I help you today?"
            elif "thank" in low:
                reply = "You're welcome! Let me know if you need anything else."
            elif "good morning" in low:
                reply = "Good morning! Ready to build something?"
            elif "good afternoon" in low:
                reply = "Good afternoon! What would you like to work on?"
            elif "what" in low and "up" in low:
                reply = "All good here! Just keeping the workspace ready. What are you working on?"
            else:
                reply = "Hi! I'm Fraiday - ask me to create, run, or research something and I'll get to work."
            reply = reply.strip()

        state["response"] = reply
        state["conversation_response"] = reply
        state["plan"] = []
        state["status"] = "completed"

        await emit(
            run_id,
            "conversational_response",
            "orchestrator",
            {
                "objective_type": objective_type,
                "response": reply,
            },
        )
        await emit(
            run_id,
            "plan_created",
            "orchestrator",
            {
                "steps": [],
                "objective_type": objective_type,
                "mode": "conversational",
            },
        )
        state["current_step"] = "end"
        return state

    # ------------------------------------------------------------
    # Existing execution planning for non-research objectives.
    # ------------------------------------------------------------

    prompt = (
        "Create an action-oriented execution plan for the objective below. "
        "Return ONLY valid JSON in this shape: "
        '{"steps":[{"id":"step_1","agent":"executor","action":"create_file",'
        '"description":"..."}]}. '
        "Use only these agents: researcher, executor, validator. "
        "Use concrete actions such as read_file, create_file, update_file, "
        "delete_file, run_command, or research.\n\n"
        "Objective:\n"
        + objective
    )

    try:
        raw = await __import__("asyncio").to_thread(
            call_groq,
            "You are the Fraiday workflow planner. Return ONLY valid JSON.",
            prompt,
        )

        data = json.loads(clean_json(raw))
        steps = data.get("steps", [])

    except Exception:
        steps = [
            {
                "id": "step_1",
                "agent": "executor",
                "action": "execute",
                "description": objective,
                "status": "pending",
            },
            {
                "id": "step_2",
                "agent": "validator",
                "action": "validate_result",
                "description": "Validate the execution result.",
                "status": "pending",
            },
        ]

    normalized = []

    for index, step in enumerate(steps, start=1):
        normalized.append(
            {
                "id": step.get("id", f"step_{index}"),
                "agent": step.get("agent", "executor"),
                "action": step.get("action", "execute"),
                "description": step.get("description", objective),
                "status": "pending",
            }
        )

    state["plan"] = normalized

    await emit(
        run_id,
        "plan_created",
        "orchestrator",
        {
            "steps": normalized,
            "objective_type": objective_type,
        },
    )

    state["current_step"] = "researcher"
    return state
