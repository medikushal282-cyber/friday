from fastapi import APIRouter, Query
from app.knowledge.store import list_knowledge, search_knowledge

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])

@router.get("")
def get_knowledge(q: str | None = Query(default=None), limit: int = 50):
    if q:
        return {"query": q, "items": search_knowledge(q, limit=limit)}
    return {"items": list_knowledge(limit=limit)}
