from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.memory import RetrieveQuery
from ..services.retriever import retrieve_hybrid


router = APIRouter()


@router.post("/", response_model=List[Dict[str, Any]])
def retrieve_memories(payload: RetrieveQuery, db: Session = Depends(get_db)):
    """Hybrid retrieval using BM25 + vector + graph expansion"""
    try:
        results = retrieve_hybrid(
            query=payload.query,
            user_id=str(payload.user_id),
            db=db,
            k=payload.limit
        )
        return results
    except Exception as e:
        from ..db import models
        q = (
            db.query(models.Memory)
            .filter(models.Memory.user_id == payload.user_id)
            .order_by(models.Memory.recall_count.desc(), models.Memory.updated_at.desc())
            .limit(payload.limit)
            .all()
        )
        return [
            {
                "id": str(m.id),
                "title": m.title,
                "content": m.content,
                "score": 0.0,
                "method": "fallback"
            }
            for m in q
        ]


