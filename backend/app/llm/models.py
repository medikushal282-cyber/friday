import os
import time
import httpx
from typing import Dict, Any, List, Optional
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

class ModelRegistry:
    def __init__(self):
        self._cache: List[ModelMetadata] = []
        self._last_fetch = 0
        self._cache_ttl = 300 # 5 minutes

    def fetch_groq_models(self) -> List[ModelMetadata]:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return []
        try:
            resp = httpx.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            models = []
            for item in data.get("data", []):
                # Only include active text models
                if not item.get("active", True):
                    continue
                # Skip models that require audio/image input, or output non-text
                if "audio" in item.get("input_modalities", []) or "image" in item.get("input_modalities", []):
                    continue
                if "speech" in item.get("output_modalities", []):
                    continue
                
                features = item.get("supported_features", [])
                tool_support = "tools" in features
                reasoning_support = "reasoning" in features
                context_window = item.get("context_window", 32768)
                
                # Model is agentic ready if it supports tools
                agent_compatible = tool_support
                
                capabilities = []
                if agent_compatible:
                    capabilities.append("tool_calling")
                if reasoning_support:
                    capabilities.append("reasoning")
                capabilities.append("fast_inference")
                
                models.append(ModelMetadata(
                    id=item["id"],
                    provider="groq",
                    display_name=item.get("name") or item["id"],
                    capabilities=capabilities,
                    reasoning_support=reasoning_support,
                    tool_support=tool_support,
                    agent_compatible=agent_compatible,
                    context_window=context_window,
                    status="available"
                ))
            
            # Sort by name for neatness
            models.sort(key=lambda m: m.display_name)
            return models
        except Exception:
            return []

    def get_all_models(self, force_refresh: bool = False) -> List[ModelMetadata]:
        now = time.time()
        if force_refresh or not self._cache or (now - self._last_fetch > self._cache_ttl):
            dynamic_models = self.fetch_groq_models()
            if dynamic_models:
                self._cache = dynamic_models
                self._last_fetch = now
        return self._cache

    def list_models(self, agent_compatible_only: bool = True) -> List[Dict[str, Any]]:
        models = self.get_all_models()
        if agent_compatible_only:
            models = [m for m in models if m.agent_compatible]
        return [m.dict() for m in models]

    def get_model(self, model_id: str) -> Optional[ModelMetadata]:
        for m in self.get_all_models():
            if m.id == model_id:
                return m
        return None

    def resolve_model_for_agent(self, agent_id: str, default_model: str, custom_routing: Optional[Dict[str, str]] = None) -> str:
        """
        Resolves model ID for an agent based on custom routing or default model.
        """
        if custom_routing and agent_id in custom_routing:
            return custom_routing[agent_id]
        return default_model

_model_registry = ModelRegistry()

def get_model_registry() -> ModelRegistry:
    return _model_registry
