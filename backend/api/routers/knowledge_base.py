"""File location in project: api/routers/knowledge_base.py"""

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.get("")
def list_knowledge_base(request: Request):
    state = request.app.state.aria
    return state.load_knowledge_base()


@router.get("/search")
def search_knowledge_base(request: Request, q: str = Query(..., min_length=1), top_k: int = 5):
    state = request.app.state.aria
    return state.correlation_agent.retrieve_similar_known_pattern(q, top_k=top_k)
