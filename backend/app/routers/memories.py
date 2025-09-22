from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.session import get_db
from ..db import models
from ..schemas.memory import MemoryCreate, MemoryRead, MemoryUpdate
from ..services.indexer import index_text
from ..services.entity_linker import link_entities_in_memory, find_related_memories

class MemoryLinkCreate(BaseModel):
    src_id: str
    dst_id: str
    relation: str


router = APIRouter()


@router.get("/users")
def list_user_ids(db: Session = Depends(get_db)):
    """Return distinct user IDs that have memories."""
    rows = db.query(models.Memory.user_id).distinct().all()
    return {"user_ids": [str(r[0]) for r in rows if r and r[0]]}


@router.post("/", response_model=MemoryRead)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db)):
    try:
        index_result = index_text(payload.content, payload.title)
        
        memory = models.Memory(
            user_id=payload.user_id,
            type=models.MemoryType(payload.type),
            title=payload.title,
            content=payload.content,
            content_summary=index_result.summary,
            embedding=index_result.embedding,
            tags=payload.tags or index_result.tags,
            entity_ids=payload.entity_ids,
            source=payload.source,
            visibility=models.MemoryVisibility(payload.visibility),
            confidence=index_result.confidence,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    db.add(memory)
    db.commit()
    db.refresh(memory)
    
    if index_result.entities:
        linked_entity_ids = link_entities_in_memory(str(memory.id), index_result.entities, db, payload.user_id)
        memory.entity_ids = linked_entity_ids
        db.commit()
    
    return memory


@router.get("/", response_model=List[MemoryRead])
def list_memories(user_id: str, db: Session = Depends(get_db)):
    return (
        db.query(models.Memory)
        .filter(models.Memory.user_id == user_id)
        .order_by(models.Memory.created_at.desc())
        .limit(100)
        .all()
    )


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory(memory_id: str, payload: MemoryUpdate, db: Session = Depends(get_db)):
    memory = db.query(models.Memory).get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    if payload.title is not None:
        memory.title = payload.title
    if payload.content is not None:
        memory.content = payload.content
    if payload.tags is not None:
        memory.tags = payload.tags
    if payload.visibility is not None:
        memory.visibility = models.MemoryVisibility(payload.visibility)

    memory.version += 1
    db.commit()
    db.refresh(memory)
    return memory


@router.delete("/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db)):
    """Delete a memory by ID"""
    memory = db.query(models.Memory).get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    memory_info = {
        "id": str(memory.id),
        "title": memory.title,
        "type": memory.type.value if memory.type else None,
        "created_at": memory.created_at.isoformat()
    }
    
    db.delete(memory)
    db.commit()
    
    return {
        "message": "Memory deleted successfully",
        "deleted_memory": memory_info
    }


@router.get("/search-by-entity")
def search_by_entity(entity_name: str, user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Search memories by entity name"""
    try:
        results = find_related_memories(entity_name, user_id, db, limit)
        return {
            "entity_name": entity_name,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching by entity: {str(e)}")


@router.get("/graph")
def get_memory_graph(user_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get memory graph data for visualization"""
    try:
        memories = db.query(models.Memory).filter(
            models.Memory.user_id == user_id
        ).limit(limit).all()
        
        if not memories:
            return {
                "nodes": [],
                "edges": [],
                "count": 0
            }
        
        memory_ids = [str(m.id) for m in memories]
        links = db.query(models.MemoryLink).filter(
            (models.MemoryLink.src_id.in_(memory_ids)) | 
            (models.MemoryLink.dst_id.in_(memory_ids))
        ).all()
        
        nodes = []
        for memory in memories:
            nodes.append({
                "id": str(memory.id),
                "label": memory.title or memory.content[:50] + "..." if len(memory.content) > 50 else memory.content,
                "title": memory.title,
                "content": memory.content,
                "type": memory.type.value if memory.type else "unknown",
                "created_at": memory.created_at.isoformat(),
                "recall_count": memory.recall_count,
                "confidence": memory.confidence,
                "tags": memory.tags or []
            })
        
        edges = []
        for link in links:
            edges.append({
                "id": str(link.id),
                "source": str(link.src_id),
                "target": str(link.dst_id),
                "relation": link.relation,
                "created_at": link.created_at.isoformat()
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "count": len(nodes)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory graph: {str(e)}")


@router.post("/links")
def create_memory_link(link_data: MemoryLinkCreate, db: Session = Depends(get_db)):
    """Create a link between two memories"""
    try:
        src_memory = db.query(models.Memory).filter(models.Memory.id == link_data.src_id).first()
        dst_memory = db.query(models.Memory).filter(models.Memory.id == link_data.dst_id).first()
        
        if not src_memory:
            raise HTTPException(status_code=404, detail="Source memory not found")
        if not dst_memory:
            raise HTTPException(status_code=404, detail="Destination memory not found")
        
        existing_link = db.query(models.MemoryLink).filter(
            models.MemoryLink.src_id == link_data.src_id,
            models.MemoryLink.dst_id == link_data.dst_id,
            models.MemoryLink.relation == link_data.relation
        ).first()
        
        if existing_link:
            raise HTTPException(status_code=400, detail="Link already exists")
        
        memory_link = models.MemoryLink(
            src_id=link_data.src_id,
            dst_id=link_data.dst_id,
            relation=link_data.relation
        )
        
        db.add(memory_link)
        db.commit()
        db.refresh(memory_link)
        
        return {
            "id": str(memory_link.id),
            "src_id": str(memory_link.src_id),
            "dst_id": str(memory_link.dst_id),
            "relation": memory_link.relation,
            "created_at": memory_link.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating memory link: {str(e)}")


