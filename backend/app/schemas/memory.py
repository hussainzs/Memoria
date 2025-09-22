from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryBase(BaseModel):
    user_id: UUID
    type: str
    title: Optional[str] = None
    content: str
    tags: List[str] = Field(default_factory=list)
    entity_ids: List[UUID] = Field(default_factory=list)
    source: Optional[str] = None
    visibility: str = "private"


class MemoryCreate(MemoryBase):
    pass


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    visibility: Optional[str] = None


class MemoryRead(MemoryBase):
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_recalled: Optional[datetime] = None
    recall_count: int
    confidence: float
    version: int

    class Config:
        from_attributes = True


class RetrieveQuery(BaseModel):
    user_id: UUID
    query: str
    limit: int = 8


class AskRequest(BaseModel):
    user_id: UUID
    question: str
    limit: int = 8


class AskResponse(BaseModel):
    answer: str
    citations: list


class FeedbackRequest(BaseModel):
    user_id: UUID
    message_id: Optional[str] = None
    correct: bool
    notes: Optional[str] = None


