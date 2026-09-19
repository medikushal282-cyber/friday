import asyncio
import json
import re

from app.events import emit
from app.llm.router import call_groq
from app.knowledge.store import search_knowledge, add_knowledge
from app.knowledge.web import research_web


def clean_json(text):
    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()

def _focused_fallback(objective: str, content: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", content or "")
    terms = set(re.findall(r"[a-zA-Z0-9_]{3,}", objective.lower()))
    ranked = sorted(
        ((len(terms & set(re.findall(r"[a-zA-Z0-9_]{3,}", sentence.lower()))), sentence.strip())
         for sentence in sentences if sentence.strip()),
        reverse=True,
    )
    selected = [sentence for score, sentence in ranked[:3] if score]
    return " ".join(selected)[:1600] if selected else (content or "")[:1600]


async def researcher_node(state):
    run_id = state["run_id"]
    objective = state["objective"]

    await emit(
        run_id,
        "agent_thinking",
        "researcher",
        {
            "summary": "Checking stored knowledge before acquiring new information."
        },
    )

    matches = await asyncio.to_thread(
        search_knowledge,
        objective,
    )

    state["knowledge_matches"] = matches

    # ------------------------------------------------------------
    # Reuse persistent knowledge when possible.
    # ------------------------------------------------------------

    if matches:
        state.setdefault("research", []).append(
            {
                "source": "knowledge_base",
                "findings": [m["content"] for m in matches],
                "sources": [
                    {
                        "title": m.get("title"),
                        "url": m.get("url"),
                        "score": m.get("score"),
                        "source_type": "knowledge_base",
                    }
                    for m in matches
                ],
                "confidence": max(
                    float(m.get("confidence", 0))
                    for m in matches
                ),
            }
        )

        await emit(
            run_id,
            "knowledge_reused",
            "researcher",
            {
                "matches": len(matches),
                "sources": [
                    {
                        "title": m.get("title"),
                        "url": m.get("url"),
                        "score": m.get("score"),
                    }
                    for m in matches
                ],
            },
        )

        # For research intents, validation is next; for execution intents, still need executor
        if state.get("objective_type") in ("research", "conversation"):
            state["current_step"] = "validator"
        else:
            state["current_step"] = "executor"
        return state

    # ------------------------------------------------------------
    # Acquire external knowledge.
    # ------------------------------------------------------------

    await emit(
        run_id,
        "research_started",
        "researcher",
        {
            "query": objective,
        },
    )

    try:
        research = await asyncio.to_thread(
            research_web,
            objective,
            3,
        )
    except Exception as exc:
        research = {
            "success": False,
            "provider": None,
            "results": [],
            "errors": [
                {
                    "provider": "unknown",
                    "error": str(exc),
                }
            ],
        }

    if not research.get("success"):
        errors = research.get("errors", [])

        await emit(
            run_id,
            "research_provider_failed",
            "researcher",
            {
                "query": objective,
                "errors": errors,
            },
        )

        state.setdefault("research", []).append(
            {
                "source": "external",
                "findings": [],
                "sources": [],
                "confidence": 0.0,
                "success": False,
                "errors": errors,
            }
        )

        # Do NOT silently convert a research failure into workspace research.
        # For execution intents, still proceed to executor even if research failed
        if state.get("objective_type") in ("research", "conversation"):
            state["current_step"] = "validator"
        else:
            state["current_step"] = "executor"
        return state

    web_results = research.get("results", [])

    sources = [
        {
            "title": item.get("title"),
            "url": item.get("url"),
            "source": item.get("source"),
            "source_type": item.get("source_type", "web"),
        }
        for item in web_results
    ]

    findings = [
        item.get("content", "")[:7000]
        for item in web_results
        if item.get("content")
    ]

    if not findings:
        await emit(
            run_id,
            "research_provider_failed",
            "researcher",
            {
                "query": objective,
                "errors": [
                    {
                        "provider": research.get("provider"),
                        "error": "Provider returned no usable research content.",
                    }
                ],
            },
        )

        state.setdefault("research", []).append(
            {
                "source": "external",
                "findings": [],
                "sources": sources,
                "confidence": 0.0,
                "success": False,
            }
        )

        if state.get("objective_type") in ("research", "conversation"):
            state["current_step"] = "validator"
        else:
            state["current_step"] = "executor"
        return state

    # ------------------------------------------------------------
    # Summarize external findings with Groq.
    # ------------------------------------------------------------

    prompt = (
        "Extract only useful facts needed to answer the objective. "
        "Return ONLY valid JSON in this exact shape: "
        '{"summary":"...","confidence":0.0}. '
        "Do not invent facts.\n\n"
        "Objective:\n"
        + objective
        + "\n\nSources:\n"
        + json.dumps(findings[:3])
    )

    try:
        raw = await asyncio.to_thread(
            call_groq,
            "You are a careful research summarizer. Return ONLY valid JSON.",
            prompt,
        )

        summary = json.loads(clean_json(raw))

    except Exception:
        summary = {
            "summary": _focused_fallback(objective, findings[0]),
            "confidence": 0.55,
        }

    content = str(summary.get("summary", "")).strip()

    if not content:
        await emit(
            run_id,
            "research_provider_failed",
            "researcher",
            {
                "query": objective,
                "errors": [
                    {
                        "provider": research.get("provider"),
                        "error": "Research was retrieved but produced no summary.",
                    }
                ],
            },
        )

        if state.get("objective_type") in ("research", "conversation"):
            state["current_step"] = "validator"
        else:
            state["current_step"] = "executor"
        return state

    confidence = float(summary.get("confidence", 0.5))

    state["knowledge_sources"] = sources

    await asyncio.to_thread(
        add_knowledge,
        objective,
        content,
        title="Fraiday research",
        url=sources[0]["url"] if sources else "",
        source_type=sources[0].get("source_type", "web") if sources else "web",
        confidence=confidence,
        relevance=1.0,
    )

    state.setdefault("research", []).append(
        {
            "source": "web",
            "provider": research.get("provider"),
            "findings": [content],
            "sources": sources,
            "confidence": confidence,
            "success": True,
        }
    )

    await emit(
        run_id,
        "knowledge_stored",
        "researcher",
        {
            "query": objective,
            "provider": research.get("provider"),
            "sources": sources,
        },
    )

    await emit(
        run_id,
        "research_completed",
        "researcher",
        {
            "provider": research.get("provider"),
            "sources": sources,
            "confidence": confidence,
        },
    )

    # Route based on intent: research → validator, execution intents → executor
    if state.get("objective_type") in ("research", "conversation"):
        state["current_step"] = "validator"
    else:
        state["current_step"] = "executor"
    return state
