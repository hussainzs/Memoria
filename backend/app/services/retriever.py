import math
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from ..db.models import Memory, MemoryLink
from ..core.config import settings
from .temporal_scorer import temporal_scorer


class RetrievalResult:
    def __init__(self, memory_id: str, score: float, memory: Memory, retrieval_method: str):
        self.memory_id = memory_id
        self.score = score
        self.memory = memory
        self.retrieval_method = retrieval_method


class HybridRetriever:
    def __init__(self, db: Session):
        self.db = db
        self.vector_dim = settings.vector_dim
    
    def retrieve_hybrid(
        self, 
        query: str, 
        user_id: str, 
        k: int = 8,
        include_graph_expansion: bool = True,
        temporal_decay: bool = True
    ) -> List[RetrievalResult]:
        """
        Hybrid retrieval combining multiple strategies
        """
        results = []
        
        bm25_results = self._bm25_search(query, user_id, k * 2)
        results.extend(bm25_results)
        
        vector_results = self._vector_search(query, user_id, k * 2)
        results.extend(vector_results)
        
        if include_graph_expansion:
            graph_results = self._graph_expansion(results, user_id, k)
            results.extend(graph_results)
        
        unique_results = self._deduplicate_results(results)
        
        if temporal_decay:
            unique_results = self._apply_temporal_scoring(unique_results)
        
        unique_results.sort(key=lambda x: x.score, reverse=True)
        return unique_results[:k]
    
    def _bm25_search(self, query: str, user_id: str, limit: int) -> List[RetrievalResult]:
        """BM25-style text search using PostgreSQL full-text search"""
        try:
            search_query = text("""
                SELECT id, title, content, created_at, recall_count, confidence,
                       ts_rank(to_tsvector('english', COALESCE(title, '') || ' ' || content), 
                               plainto_tsquery('english', :query)) as rank
                FROM memories 
                WHERE user_id = :user_id 
                AND to_tsvector('english', COALESCE(title, '') || ' ' || content) @@ plainto_tsquery('english', :query)
                ORDER BY rank DESC
                LIMIT :limit
            """)
            
            results = self.db.execute(search_query, {
                'query': query,
                'user_id': user_id,
                'limit': limit
            }).fetchall()
            
            return [
                RetrievalResult(
                    memory_id=str(row.id),
                    score=float(row.rank),
                    memory=self.db.query(Memory).get(row.id),
                    retrieval_method="bm25"
                )
                for row in results
            ]
        except Exception as e:
            print(f"BM25 search error: {e}")
            return []
    
    def _vector_search(self, query: str, user_id: str, limit: int) -> List[RetrievalResult]:
        """Vector similarity search using pgvector"""
        try:
            return []
        except Exception as e:
            print(f"Vector search error: {e}")
            return []
    
    def _graph_expansion(self, initial_results: List[RetrievalResult], user_id: str, k: int) -> List[RetrievalResult]:
        """Expand results using graph relationships"""
        if not initial_results:
            return []
        
        memory_ids = [result.memory_id for result in initial_results]
        
        try:
            linked_memories = self.db.query(Memory).join(
                MemoryLink, 
                or_(
                    and_(MemoryLink.src_id.in_(memory_ids), MemoryLink.dst_id == Memory.id),
                    and_(MemoryLink.dst_id.in_(memory_ids), MemoryLink.src_id == Memory.id)
                )
            ).filter(Memory.user_id == user_id).limit(k).all()
            
            return [
                RetrievalResult(
                    memory_id=str(memory.id),
                    score=0.3,
                    memory=memory,
                    retrieval_method="graph_expansion"
                )
                for memory in linked_memories
            ]
        except Exception as e:
            print(f"Graph expansion error: {e}")
            return []
    
    def _deduplicate_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Remove duplicate memories and combine scores"""
        memory_scores = {}
        
        for result in results:
            memory_id = result.memory_id
            if memory_id in memory_scores:
                memory_scores[memory_id].score = max(
                    memory_scores[memory_id].score, 
                    result.score
                )
            else:
                memory_scores[memory_id] = result
        
        return list(memory_scores.values())
    
    def _apply_temporal_scoring(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Apply enhanced temporal scoring to retrieval results"""
        for result in results:
            memory = result.memory
            base_score = result.score
            
            temporal_score = temporal_scorer.calculate_temporal_score(memory)
            
            final_score = (0.7 * base_score) + (0.3 * temporal_score)
            
            result.score = max(0.0, final_score)
        
        return results
    
    def search_by_tags(self, tags: List[str], user_id: str, k: int = 8) -> List[RetrievalResult]:
        """Search memories by tags"""
        try:
            memories = self.db.query(Memory).filter(
                Memory.user_id == user_id,
                Memory.tags.op('&&')(tags)
            ).limit(k).all()
            
            return [
                RetrievalResult(
                    memory_id=str(memory.id),
                    score=0.8,
                    memory=memory,
                    retrieval_method="tag_search"
                )
                for memory in memories
            ]
        except Exception as e:
            print(f"Tag search error: {e}")
            return []
    
    def search_by_entities(self, entity_names: List[str], user_id: str, k: int = 8) -> List[RetrievalResult]:
        """Search memories by entity names"""
        try:
            conditions = []
            for entity in entity_names:
                pattern = f"%{entity}%"
                conditions.append(Memory.title.ilike(pattern))
                conditions.append(Memory.content.ilike(pattern))
            
            if not conditions:
                return []
            
            memories = (
                self.db.query(Memory)
                .filter(
                    Memory.user_id == user_id,
                    or_(*conditions)
                )
                .limit(k)
                .all()
            )
            
            return [
                RetrievalResult(
                    memory_id=str(memory.id),
                    score=0.7,
                    memory=memory,
                    retrieval_method="entity_search"
                )
                for memory in memories
            ]
        except Exception as e:
            print(f"Entity search error: {e}")
            return []


def retrieve_hybrid(query: str, user_id: str, db: Session, k: int = 8) -> List[Dict[str, Any]]:
    """Convenience function for hybrid retrieval"""
    retriever = HybridRetriever(db)
    results = retriever.retrieve_hybrid(query, user_id, k)
    
    return [
        {
            "id": result.memory_id,
            "title": result.memory.title,
            "content": result.memory.content,
            "score": result.score,
            "method": result.retrieval_method,
            "created_at": result.memory.created_at.isoformat(),
            "recall_count": result.memory.recall_count,
            "confidence": result.memory.confidence
        }
        for result in results
    ]


