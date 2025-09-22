from datetime import datetime, timedelta
from math import exp, log
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..db.models import Memory, MemoryType, MemoryVisibility


class ConsolidationPolicy:
    def __init__(
        self,
        w1: float = 0.4,
        w2: float = 0.3,
        w3: float = 0.2,
        w4: float = 0.1,
        lam: float = 0.05,
        stm_threshold: float = 0.3,
        mtm_threshold: float = 0.6,
        ltm_threshold: float = 0.8
    ):
        self.w1 = w1
        self.w2 = w2
        self.w3 = w3
        self.w4 = w4
        self.lam = lam
        self.stm_threshold = stm_threshold
        self.mtm_threshold = mtm_threshold
        self.ltm_threshold = ltm_threshold


class MemoryManager:
    def __init__(self, db: Session, policy: Optional[ConsolidationPolicy] = None):
        self.db = db
        self.policy = policy or ConsolidationPolicy()
    
    def compute_consolidation_score(
        self,
        recall_count: int,
        age_days: float,
        relevance_score: float,
        user_feedback: float,
        content_length: int = 0,
        entity_count: int = 0,
        tag_count: int = 0
    ) -> float:
        """
        Enhanced consolidation scoring with additional factors
        """
        normalised_freq = log(1 + recall_count) / log(10)
        
        normalised_recency = exp(-self.policy.lam * age_days)
        
        content_quality = min(1.0, content_length / 1000)
        
        entity_richness = min(1.0, entity_count / 10)
        
        tag_richness = min(1.0, tag_count / 5)
        
        # Calculate composite score
        score = (
            self.policy.w1 * normalised_freq +
            self.policy.w2 * normalised_recency +
            self.policy.w3 * relevance_score +
            self.policy.w4 * user_feedback +
            0.1 * content_quality +
            0.05 * entity_richness +
            0.05 * tag_richness
        )
        
        return min(1.0, max(0.0, score))
    
    def determine_memory_tier(self, score: float) -> str:
        """Determine memory tier based on consolidation score"""
        if score >= self.policy.ltm_threshold:
            return "LTM"
        elif score >= self.policy.mtm_threshold:
            return "MTM"
        else:
            return "STM"
    
    def should_promote_memory(self, memory: Memory) -> bool:
        """Check if memory should be promoted to higher tier"""
        score = self.compute_consolidation_score(
            recall_count=memory.recall_count,
            age_days=(datetime.utcnow() - memory.created_at).days,
            relevance_score=memory.confidence,
            user_feedback=0.0,
            content_length=len(memory.content),
            entity_count=len(memory.entity_ids),
            tag_count=len(memory.tags)
        )
        
        current_tier = self.determine_memory_tier(score)
        
        if current_tier == "LTM" and memory.visibility == MemoryVisibility.private:
            return True
        elif current_tier == "MTM" and memory.recall_count > 5:
            return True
        elif current_tier == "STM" and memory.recall_count > 2:
            return True
        
        return False
    
    def should_prune_memory(self, memory: Memory) -> bool:
        """Check if memory should be pruned/forgotten"""
        days_since_recall = (datetime.utcnow() - (memory.last_recalled or memory.created_at)).days
        score = self.compute_consolidation_score(
            recall_count=memory.recall_count,
            age_days=(datetime.utcnow() - memory.created_at).days,
            relevance_score=memory.confidence,
            user_feedback=0.0,
            content_length=len(memory.content),
            entity_count=len(memory.entity_ids),
            tag_count=len(memory.tags)
        )
        
        return score < 0.2 and days_since_recall > 30
    
    def consolidate_memories(self, user_id: str, batch_size: int = 100) -> Dict[str, int]:
        """Run consolidation process for a user's memories"""
        stats = {"promoted": 0, "pruned": 0, "processed": 0}
        
        memories = self.db.query(Memory).filter(
            Memory.user_id == user_id
        ).limit(batch_size).all()
        
        for memory in memories:
            stats["processed"] += 1
            
            if self.should_promote_memory(memory):
                self._promote_memory(memory)
                stats["promoted"] += 1
            
            elif self.should_prune_memory(memory):
                self._prune_memory(memory)
                stats["pruned"] += 1
        
        return stats
    
    def _promote_memory(self, memory: Memory):
        """Promote memory to higher tier"""
        score = self.compute_consolidation_score(
            recall_count=memory.recall_count,
            age_days=(datetime.utcnow() - memory.created_at).days,
            relevance_score=memory.confidence,
            user_feedback=0.0,
            content_length=len(memory.content),
            entity_count=len(memory.entity_ids),
            tag_count=len(memory.tags)
        )
        
        tier = self.determine_memory_tier(score)
        
        if tier == "LTM":
            memory.visibility = MemoryVisibility.shared
            memory.confidence = min(1.0, memory.confidence + 0.1)
        elif tier == "MTM":
            memory.confidence = min(1.0, memory.confidence + 0.05)
        
        self.db.commit()
    
    def _prune_memory(self, memory: Memory):
        """Soft delete memory (mark for deletion)"""
        memory.confidence = max(0.1, memory.confidence * 0.5)
        self.db.commit()
    
    def compress_episodic_memories(self, user_id: str, memory_type: MemoryType) -> Optional[Memory]:
        """Compress multiple episodic memories into a single semantic memory"""
        episodic_memories = self.db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.type == memory_type,
            Memory.confidence > 0.5
        ).order_by(Memory.created_at.desc()).limit(10).all()
        
        if len(episodic_memories) < 3:
            return None
        
        compressed_content = self._create_compressed_content(episodic_memories)
        compressed_title = f"Summary of {memory_type.value} memories"
        
        compressed_memory = Memory(
            user_id=user_id,
            type=memory_type,
            title=compressed_title,
            content=compressed_content,
            visibility=MemoryVisibility.private,
            confidence=0.8,
            source="system_compression"
        )
        
        self.db.add(compressed_memory)
        self.db.commit()
        
        for episodic_memory in episodic_memories:
            link = MemoryLink(
                src_id=compressed_memory.id,
                dst_id=episodic_memory.id,
                relation="compresses"
            )
            self.db.add(link)
        
        self.db.commit()
        return compressed_memory
    
    def _create_compressed_content(self, memories: List[Memory]) -> str:
        """Create compressed content from multiple memories"""
        titles = [mem.title for mem in memories if mem.title]
        contents = [mem.content for mem in memories]
        
        compressed = f"Summary of {len(memories)} memories:\n\n"
        
        if titles:
            compressed += f"Topics: {', '.join(titles[:5])}\n\n"
        
        all_text = " ".join(contents)
        words = all_text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 4:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        key_phrases = [word for word, freq in top_words if freq > 1]
        
        if key_phrases:
            compressed += f"Key themes: {', '.join(key_phrases)}\n\n"
        
        sample_content = contents[0][:200] + "..." if len(contents[0]) > 200 else contents[0]
        compressed += f"Sample content: {sample_content}"
        
        return compressed


def compute_consolidation_score(
    recall_count: int, 
    age_days: float, 
    relevance_score: float, 
    user_feedback: float,
    w1: float = 0.4, 
    w2: float = 0.3, 
    w3: float = 0.2, 
    w4: float = 0.1, 
    lam: float = 0.05
) -> float:
    """Legacy function for backward compatibility"""
    manager = MemoryManager(None)  # No DB needed for just scoring
    return manager.compute_consolidation_score(
        recall_count, age_days, relevance_score, user_feedback
    )


def should_prune(score: float, days_since_recall: int) -> bool:
    """Legacy function for backward compatibility"""
    return score < 0.25 and days_since_recall > 30


