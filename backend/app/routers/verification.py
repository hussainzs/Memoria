"""
Verification endpoints for answer validation and hallucination detection
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..db.session import get_db
from ..db import models
from ..services.verifier import verifier, verify_answer
from ..core.config import settings

router = APIRouter()


class VerificationRequest(BaseModel):
    answer: str
    question: str
    memory_ids: List[str]


class VerificationResponse(BaseModel):
    is_verified: bool
    confidence: float
    fact_check_score: float
    citation_score: float
    consistency_score: float
    issues: List[str]
    suggestions: List[str]


@router.post("/verify-answer", response_model=VerificationResponse)
def verify_answer_endpoint(request: VerificationRequest, db: Session = Depends(get_db)):
    """Verify an answer against specific memories"""
    try:
        memories = db.query(models.Memory).filter(
            models.Memory.id.in_(request.memory_ids)
        ).all()
        
        if not memories:
            raise HTTPException(status_code=404, detail="No memories found with provided IDs")
        
        verification_result = verify_answer(
            answer=request.answer,
            memories=memories,
            question=request.question
        )
        
        return VerificationResponse(
            is_verified=verification_result.is_verified,
            confidence=verification_result.confidence,
            fact_check_score=verification_result.fact_check_score,
            citation_score=verification_result.citation_score,
            consistency_score=verification_result.consistency_score,
            issues=verification_result.issues,
            suggestions=verification_result.suggestions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error verifying answer: {str(e)}")


@router.get("/verification-stats")
def get_verification_stats(user_id: str, db: Session = Depends(get_db)):
    """Get verification statistics for a user's memories"""
    try:
        memories = db.query(models.Memory).filter(
            models.Memory.user_id == user_id
        ).all()
        
        if not memories:
            return {
                "user_id": user_id,
                "total_memories": 0,
                "verification_stats": {}
            }
        
        total_memories = len(memories)
        high_confidence_memories = sum(1 for memory in memories if memory.confidence >= 0.8)
        medium_confidence_memories = sum(1 for memory in memories if 0.5 <= memory.confidence < 0.8)
        low_confidence_memories = sum(1 for memory in memories if memory.confidence < 0.5)
        
        avg_confidence = sum(memory.confidence for memory in memories) / total_memories
        
        memory_types = {}
        for memory in memories:
            memory_type = memory.type.value if memory.type else "unknown"
            memory_types[memory_type] = memory_types.get(memory_type, 0) + 1
        
        return {
            "user_id": user_id,
            "total_memories": total_memories,
            "verification_stats": {
                "average_confidence": round(avg_confidence, 3),
                "confidence_distribution": {
                    "high_confidence": high_confidence_memories,
                    "medium_confidence": medium_confidence_memories,
                    "low_confidence": low_confidence_memories
                },
                "memory_types": memory_types,
                "confidence_by_type": {
                    memory_type: round(
                        sum(m.confidence for m in memories if (m.type.value if m.type else "unknown") == memory_type) / 
                        memory_types[memory_type], 3
                    )
                    for memory_type in memory_types
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting verification stats: {str(e)}")


@router.get("/test-verification")
def test_verification(user_id: str, db: Session = Depends(get_db)):
    """Test verification with a sample answer"""
    try:
        sample_memory = db.query(models.Memory).filter(
            models.Memory.user_id == user_id
        ).first()
        
        if not sample_memory:
            raise HTTPException(status_code=404, detail="No memories found for user")
        
        test_cases = [
            {
                "name": "Accurate Answer",
                "answer": f"Based on my knowledge: {sample_memory.content[:100]}...",
                "question": "What do you know about this topic?"
            },
            {
                "name": "Partially Accurate Answer",
                "answer": f"Based on my knowledge: {sample_memory.content[:50]}... and some additional unrelated information that is not in my memories.",
                "question": "What do you know about this topic?"
            },
            {
                "name": "Inaccurate Answer",
                "answer": "I don't have any information about this topic in my memories.",
                "question": "What do you know about this topic?"
            }
        ]
        
        results = []
        for test_case in test_cases:
            verification_result = verify_answer(
                answer=test_case["answer"],
                memories=[sample_memory],
                question=test_case["question"]
            )
            
            results.append({
                "test_name": test_case["name"],
                "answer": test_case["answer"],
                "is_verified": verification_result.is_verified,
                "confidence": verification_result.confidence,
                "fact_check_score": verification_result.fact_check_score,
                "citation_score": verification_result.citation_score,
                "consistency_score": verification_result.consistency_score,
                "issues": verification_result.issues,
                "suggestions": verification_result.suggestions
            })
        
        return {
            "user_id": user_id,
            "test_results": results,
            "sample_memory_id": str(sample_memory.id),
            "sample_memory_content": sample_memory.content[:200] + "..." if len(sample_memory.content) > 200 else sample_memory.content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing verification: {str(e)}")


@router.get("/verification-health")
def get_verification_health():
    """Check if verification service is healthy"""
    try:
        # Check if LLM client is available
        llm_available = verifier.llm is not None and verifier.llm.is_available()
        provider = getattr(settings, "llm_provider", "ollama")
        
        return {
            "status": "healthy",
            "llm_provider": provider,
            "llm_available": llm_available,
            "verification_method": "enhanced" if llm_available else "fallback",
            "features": {
                "fact_checking": True,
                "citation_validation": True,
                "consistency_checking": True,
                "llm_verification": llm_available
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "llm_available": False,
            "verification_method": "fallback"
        }

