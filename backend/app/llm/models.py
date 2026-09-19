from typing import Dict, Any, List, Optional
import os
import httpx
from pydantic import BaseModel

class ModelMetadata(BaseModel):
    id: str
    provider: str
    display_name: str
    capabilities: List[str]
    reasoning_support: bool = False
    tool_support: bool = True
    agent_compatible: bool = True
    context_window: int = 32768
    status: str = "available"

DEFAULT_MODELS: List[ModelMetadata] = [
    ModelMetadata(
        id="qwen/qwen3.8-27b",
        provider="groq",
        display_name="Qwen 3.8 27B (Groq)",
        capabilities=["coding", "fast_inference", "tool_calling", "agentic_reasoning"],
        reasoning_support=True,
        tool_support=True,
        agent_compatible=True,
        context_window=32768
    ),
    ModelMetadata(
        id="llama-3.3-70b-versatile",
        provider="groq",
        display_name="Llama 3.3 70B Versatile (Groq)",
        capabilities=["coding", "general_reasoning", "tool_calling"],
        reasoning_support=True,
        tool_support=True,
        agent_compatible=True,
        context_window=128000
    ),
    ModelMetadata(
        id="llama-3.1-8b-instant",
        provider="groq",
        display_name="Llama 3.1 8B Instant (Groq)",
        capabilities=["fast_inference", "simple_tasks"],
        reasoning_support=False,
        tool_support=True,
        agent_compatible=True,
        context_window=128000
    ),
    ModelMetadata(
        id="openai/gpt-4o",
        provider="openai",
        display_name="GPT-4o (OpenAI)",
        capabilities=["deep_reasoning", "multimodal", "complex_refactoring"],
        reasoning_support=True,
        tool_support=True,
        agent_compatible=True,
        context_window=128000
    ),
    ModelMetadata(
        id="openai/gpt-4o-mini",
        provider="openai",
        display_name="GPT-4o Mini (OpenAI)",
        capabilities=["fast_inference", "routine_coding"],
        reasoning_support=False,
        tool_support=True,
        agent_compatible=True,
        context_window=128000
    )
]

class ModelRegistry:
    def __init__(self):
        self._models: Dict[str, ModelMetadata] = {m.id: m for m in DEFAULT_MODELS}

    def list_models(self, agent_compatible_only: bool = True) -> List[Dict[str, Any]]:
        models = list(self._models.values())
        if agent_compatible_only:
            models = [m for m in models if m.agent_compatible]
        
        # Check live availability based on server-side environment variables
        has_groq = bool(os.environ.get("GROQ_API_KEY"))
        has_openai = bool(os.environ.get("OPENAI_API_KEY"))

        result = []
        for m in models:
            d = m.dict()
            if m.provider == "groq":
                d["status"] = "available" if has_groq else "unconfigured"
            elif m.provider == "openai":
                d["status"] = "available" if has_openai else "unconfigured"
            result.append(d)
        return result

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        return self._models.get(model_id)

    def resolve_model_for_agent(self, agent_id: str, custom_routing: Optional[Dict[str, str]] = None) -> str:
        """
        Resolves model ID for an agent based on custom routing, agent defaults, or global fallback.
        """
        if custom_routing and agent_id in custom_routing:
            return custom_routing[agent_id]
        
        # Optimal defaults per specialized agent
        agent_defaults = {
            "orchestrator": "qwen/qwen3.8-27b",
            "researcher": "llama-3.3-70b-versatile",
            "coding_agent": "qwen/qwen3.8-27b",
            "testing_agent": "llama-3.1-8b-instant",
            "debugging_agent": "qwen/qwen3.8-27b",
            "data_agent": "qwen/qwen3.8-27b",
            "review_agent": "qwen/qwen3.8-27b"
        }
        return agent_defaults.get(agent_id, "qwen/qwen3.8-27b")

_model_registry = ModelRegistry()

def get_model_registry() -> ModelRegistry:
    return _model_registry
