"""
Temporal analysis endpoints for memory patterns and insights
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..db import models
from ..services.temporal_scorer import temporal_scorer

router = APIRouter()


@router.get("/boosted-memories")
def get_boosted_memories(user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get memories that are currently receiving temporal boost"""
    try:
        boosted_memories = temporal_scorer.get_temporal_boost_memories(user_id, db, limit)
        
        return {
            "user_id": user_id,
            "boosted_memories": [
                {
                    "id": str(memory.id),
                    "title": memory.title,
                    "content": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                    "created_at": memory.created_at.isoformat(),
                    "last_recalled": memory.last_recalled.isoformat() if memory.last_recalled else None,
                    "recall_count": memory.recall_count,
                    "confidence": memory.confidence
                }
                for memory in boosted_memories
            ],
            "count": len(boosted_memories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting boosted memories: {str(e)}")


@router.get("/decaying-memories")
def get_decaying_memories(user_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """Get memories that are decaying and might need attention"""
    try:
        decaying_memories = temporal_scorer.get_decaying_memories(user_id, db, limit)
        
        return {
            "user_id": user_id,
            "decaying_memories": [
                {
                    "id": str(memory.id),
                    "title": memory.title,
                    "content": memory.content[:200] + "..." if len(memory.content) > 200 else memory.content,
                    "created_at": memory.created_at.isoformat(),
                    "last_recalled": memory.last_recalled.isoformat() if memory.last_recalled else None,
                    "recall_count": memory.recall_count,
                    "confidence": memory.confidence
                }
                for memory in decaying_memories
            ],
            "count": len(decaying_memories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting decaying memories: {str(e)}")


@router.get("/temporal-scores")
def get_temporal_scores(user_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """Get temporal scores for recent memories"""
    try:
        recent_memories = db.query(models.Memory).filter(
            models.Memory.user_id == user_id
        ).order_by(
            models.Memory.created_at.desc()
        ).limit(limit).all()
        
        scored_memories = []
        for memory in recent_memories:
            temporal_score = temporal_scorer.calculate_temporal_score(memory)
            scored_memories.append({
                "id": str(memory.id),
                "title": memory.title,
                "created_at": memory.created_at.isoformat(),
                "last_recalled": memory.last_recalled.isoformat() if memory.last_recalled else None,
                "recall_count": memory.recall_count,
                "temporal_score": temporal_score,
                "confidence": memory.confidence
            })
        
        scored_memories.sort(key=lambda x: x['temporal_score'], reverse=True)
        
        return {
            "user_id": user_id,
            "scored_memories": scored_memories,
            "count": len(scored_memories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting temporal scores: {str(e)}")


@router.get("/memory-insights")
def get_memory_insights(user_id: str, db: Session = Depends(get_db)):
    """Get insights about memory patterns and temporal behavior"""
    try:
        all_memories = db.query(models.Memory).filter(
            models.Memory.user_id == user_id
        ).all()
        
        if not all_memories:
            return {
                "user_id": user_id,
                "total_memories": 0,
                "insights": {}
            }
        
        total_memories = len(all_memories)
        total_recalls = sum(memory.recall_count or 0 for memory in all_memories)
        avg_recalls = total_recalls / total_memories if total_memories > 0 else 0
        
        memory_types = {}
        for memory in all_memories:
            memory_type = memory.type.value if memory.type else "unknown"
            memory_types[memory_type] = memory_types.get(memory_type, 0) + 1
        
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        
        recent_memories = sum(1 for memory in all_memories 
                            if (now - memory.created_at).days <= 7)
        old_memories = sum(1 for memory in all_memories 
                         if (now - memory.created_at).days > 30)
        
        boosted_count = len(temporal_scorer.get_temporal_boost_memories(user_id, db, 100))
        decaying_count = len(temporal_scorer.get_decaying_memories(user_id, db, 100))
        
        insights = {
            "total_memories": total_memories,
            "total_recalls": total_recalls,
            "average_recalls_per_memory": round(avg_recalls, 2),
            "memory_types": memory_types,
            "temporal_distribution": {
                "recent_memories_7_days": recent_memories,
                "old_memories_30_days": old_memories,
                "boosted_memories": boosted_count,
                "decaying_memories": decaying_count
            },
            "recall_patterns": {
                "highly_recalled": sum(1 for memory in all_memories if (memory.recall_count or 0) > 5),
                "never_recalled": sum(1 for memory in all_memories if (memory.recall_count or 0) == 0),
                "recently_recalled": sum(1 for memory in all_memories 
                                      if memory.last_recalled and (now - memory.last_recalled).days <= 7)
            }
        }
        
        return {
            "user_id": user_id,
            "insights": insights
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting memory insights: {str(e)}")

