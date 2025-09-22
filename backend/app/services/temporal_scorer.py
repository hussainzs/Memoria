"""
Temporal scoring service for memory relevance based on time and frequency
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db.models import Memory


class TemporalScorer:
    def __init__(self):
        self.half_life_days = 30
        self.recency_boost_days = 7
        self.frequency_weight = 0.3
        self.recency_weight = 0.7
        
    def calculate_temporal_score(
        self, 
        memory: Memory, 
        current_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate temporal relevance score for a memory
        
        Args:
            memory: Memory object to score
            current_time: Current time (defaults to now)
            
        Returns:
            Temporal score between 0 and 1
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        recency_score = self._calculate_recency_score(memory, current_time)
        
        frequency_score = self._calculate_frequency_score(memory)
        
        decay_factor = self._calculate_decay_factor(memory, current_time)
        
        temporal_score = (
            self.recency_weight * recency_score + 
            self.frequency_weight * frequency_score
        ) * decay_factor
        
        return max(0.0, min(1.0, temporal_score))
    
    def _calculate_recency_score(self, memory: Memory, current_time: datetime) -> float:
        """Calculate recency score based on creation and last access time"""
        reference_time = memory.last_recalled if memory.last_recalled else memory.created_at
        
        days_ago = (current_time - reference_time).total_seconds() / (24 * 3600)
        
        if days_ago <= self.recency_boost_days:
            boost_factor = 1.0 + (self.recency_boost_days - days_ago) / self.recency_boost_days * 0.5
            days_ago = days_ago / boost_factor
        
        recency_score = math.exp(-days_ago / self.half_life_days)
        
        return recency_score
    
    def _calculate_frequency_score(self, memory: Memory) -> float:
        """Calculate frequency score based on recall count"""
        recall_count = memory.recall_count or 0
        
        if recall_count == 0:
            return 0.5
        else:
            max_expected_recalls = 100
            frequency_score = math.log(1 + recall_count) / math.log(1 + max_expected_recalls)
            return min(1.0, frequency_score)
    
    def _calculate_decay_factor(self, memory: Memory, current_time: datetime) -> float:
        """Calculate decay factor based on memory age"""
        days_old = (current_time - memory.created_at).total_seconds() / (24 * 3600)
        
        if days_old <= self.half_life_days:
            decay_factor = 1.0
        else:
            extra_days = days_old - self.half_life_days
            decay_factor = math.exp(-extra_days / (self.half_life_days * 2))
        
        return decay_factor
    
    def apply_temporal_scoring(
        self, 
        memories: List[Dict[str, Any]], 
        current_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply temporal scoring to a list of memories
        """
        if current_time is None:
            current_time = datetime.utcnow()
        
        scored_memories = []
        for memory_data in memories:
            temp_memory = Memory(
                id=memory_data.get('id'),
                created_at=memory_data.get('created_at', current_time),
                last_recalled=memory_data.get('last_recalled'),
                recall_count=memory_data.get('recall_count', 0)
            )
            
            temporal_score = self.calculate_temporal_score(temp_memory, current_time)
            
            memory_data['temporal_score'] = temporal_score
            scored_memories.append(memory_data)
        
        return scored_memories
    
    def update_recall_stats(self, memory: Memory, db: Session) -> None:
        """
        Update recall statistics for a memory
        """
        current_time = datetime.utcnow()
        memory.recall_count = (memory.recall_count or 0) + 1
        memory.last_recalled = current_time
        db.commit()
    
    def get_temporal_boost_memories(
        self, 
        user_id: str, 
        db: Session, 
        limit: int = 10
    ) -> List[Memory]:
        """
        Get memories that should receive temporal boost
        """
        current_time = datetime.utcnow()
        boost_threshold = current_time - timedelta(days=self.recency_boost_days)
        
        boosted_memories = db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.created_at >= boost_threshold
        ).order_by(
            Memory.created_at.desc()
        ).limit(limit).all()
        
        return boosted_memories
    
    def get_decaying_memories(
        self, 
        user_id: str, 
        db: Session, 
        limit: int = 10
    ) -> List[Memory]:
        """
        Get memories that are decaying and might need attention
        """
        current_time = datetime.utcnow()
        decay_threshold = current_time - timedelta(days=self.half_life_days * 2)
        
        decaying_memories = db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.created_at <= decay_threshold,
            Memory.recall_count <= 1
        ).order_by(
            Memory.created_at.asc()
        ).limit(limit).all()
        
        return decaying_memories


temporal_scorer = TemporalScorer()


def calculate_temporal_score(memory: Memory, current_time: Optional[datetime] = None) -> float:
    """Convenience function for calculating temporal score"""
    return temporal_scorer.calculate_temporal_score(memory, current_time)


def apply_temporal_scoring(memories: List[Dict[str, Any]], current_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Convenience function for applying temporal scoring"""
    return temporal_scorer.apply_temporal_scoring(memories, current_time)


def update_recall_stats(memory: Memory, db: Session) -> None:
    """Convenience function for updating recall statistics"""
    temporal_scorer.update_recall_stats(memory, db)

