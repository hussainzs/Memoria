from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..schemas.memory import AskRequest, AskResponse
from ..services.orchestrator import run_orchestration


router = APIRouter()


@router.post("/", response_model=AskResponse)
def ask(payload: AskRequest, db: Session = Depends(get_db)) -> Any:
    """Ask a question using the full orchestration pipeline"""
    try:
        result = run_orchestration(
            question=payload.question,
            user_id=str(payload.user_id),
            db=db
        )
        
        return AskResponse(
            answer=result["answer"],
            citations=result["citations"]
        )
    except Exception as e:
        return AskResponse(
            answer=f"I encountered an error processing your question: {str(e)}",
            citations=[]
        )


