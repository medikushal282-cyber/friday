from app.agents.registry import get_agent_registry
from app.llm.models import get_model_registry

def test_agent_registry():
    reg = get_agent_registry()
    agents = reg.list_agents()
    assert len(agents) >= 5
    agent_ids = [a["id"] for a in agents]
    assert "orchestrator" in agent_ids
    assert "coding_agent" in agent_ids
    assert "testing_agent" in agent_ids

    # Dynamic selection
    sel = reg.select_agents_for_objective("Create factorial.py and run it")
    assert "coding_agent" in sel
    assert "testing_agent" in sel

def test_model_registry():
    reg = get_model_registry()
    models = reg.list_models()
    assert len(models) >= 2
    qwen = reg.get_model("qwen/qwen3.8-27b")
    assert qwen is not None
    assert qwen.agent_compatible is True

    # Routing resolution
    resolved = reg.resolve_model_for_agent("coding_agent")
    assert resolved == "qwen/qwen3.8-27b"
