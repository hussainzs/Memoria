from fastapi import APIRouter
from ..schemas.memory import FeedbackRequest


router = APIRouter()


@router.post("/")
def submit_feedback(payload: FeedbackRequest):
    return {"status": "ok"}


