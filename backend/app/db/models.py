import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector


Base = declarative_base()


class MemoryVisibility(enum.Enum):
    private = "private"
    shared = "shared"
    public = "public"


class MemoryType(enum.Enum):
    preference = "preference"
    fact = "fact"
    event = "event"
    entity = "entity"
    media = "media"
    skill = "skill"
    instruction = "instruction"


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Memory(Base):
    __tablename__ = "memories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    type = Column(Enum(MemoryType, name="memory_type"), nullable=False)
    title = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    content_summary = Column(Text, nullable=True)
    embedding = Column(Vector(dim=384))
    tags = Column(ARRAY(String), default=list)
    entity_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)
    source = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_recalled = Column(DateTime, nullable=True)
    recall_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.5)
    visibility = Column(Enum(MemoryVisibility, name="memory_visibility"), default=MemoryVisibility.private)
    version = Column(Integer, default=1)

    outgoing_links = relationship("MemoryLink", back_populates="source_memory", foreign_keys="MemoryLink.src_id")
    incoming_links = relationship("MemoryLink", back_populates="target_memory", foreign_keys="MemoryLink.dst_id")


class MemoryLink(Base):
    __tablename__ = "memory_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    src_id = Column(UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    dst_id = Column(UUID(as_uuid=True), ForeignKey("memories.id", ondelete="CASCADE"), nullable=False, index=True)
    relation = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    source_memory = relationship("Memory", foreign_keys=[src_id], back_populates="outgoing_links")
    target_memory = relationship("Memory", foreign_keys=[dst_id], back_populates="incoming_links")


