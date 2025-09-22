"""
Cross-encoder reranking service for improving memory retrieval relevance
"""
import os
from typing import List, Tuple, Dict, Any
from sentence_transformers import CrossEncoder
from ..core.config import settings


class CrossEncoderReranker:
    def __init__(self):
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the cross-encoder model"""
        try:
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            print("Loaded cross-encoder model for reranking")
        except Exception as e:
            print(f"Failed to load cross-encoder model: {e}")
            self.model = None

    def rerank_memories(
        self, 
        query: str, 
        memories: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank memories based on query-document semantic similarity
        
        Args:
            query: The search query
            memories: List of memory dictionaries with 'content' and 'title' fields
            top_k: Number of top results to return
            
        Returns:
            Reranked list of memories with updated scores
        """
        if not self.model or not memories:
            return memories[:top_k]

        try:
            query_doc_pairs = []
            for memory in memories:
                title = memory.get('title', '')
                content = memory.get('content', '')
                
                if title and content:
                    doc_text = f"{title}: {content}"
                elif title:
                    doc_text = title
                else:
                    doc_text = content
                
                query_doc_pairs.append([query, doc_text])

            relevance_scores = self.model.predict(query_doc_pairs)
            
            scored_memories = []
            for i, memory in enumerate(memories):
                scored_memory = memory.copy()
                scored_memory['rerank_score'] = float(relevance_scores[i])
                scored_memories.append(scored_memory)

            scored_memories.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            return scored_memories[:top_k]

        except Exception as e:
            print(f"Error in cross-encoder reranking: {e}")
            return memories[:top_k]

    def rerank_retrieval_results(
        self, 
        query: str, 
        retrieval_results: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank retrieval results from the hybrid retriever
        
        Args:
            query: The search query
            retrieval_results: Results from hybrid retrieval
            top_k: Number of top results to return
            
        Returns:
            Reranked results with combined scores
        """
        if not retrieval_results:
            return []

        memories = []
        for result in retrieval_results:
            memory = {
                'id': result.get('id'),
                'title': result.get('title', ''),
                'content': result.get('content', ''),
                'original_score': result.get('score', 0.0),
                'method': result.get('method', 'unknown')
            }
            memories.append(memory)

        reranked_memories = self.rerank_memories(query, memories, top_k)

        reranked_results = []
        for memory in reranked_memories:
            result = {
                'id': memory['id'],
                'title': memory.get('title', ''),
                'content': memory.get('content', ''),
                'score': memory.get('rerank_score', memory.get('original_score', 0.0)),
                'method': f"{memory.get('method', 'unknown')}_reranked",
                'original_score': memory.get('original_score', 0.0),
                'rerank_score': memory.get('rerank_score', 0.0)
            }
            reranked_results.append(result)

        return reranked_results

    def calculate_relevance_score(self, query: str, memory_content: str) -> float:
        """
        Calculate relevance score for a single query-memory pair
        
        Args:
            query: The search query
            memory_content: The memory content to score
            
        Returns:
            Relevance score between 0 and 1
        """
        if not self.model:
            return 0.0

        try:
            score = self.model.predict([[query, memory_content]])
            return float(score[0])
        except Exception as e:
            print(f"Error calculating relevance score: {e}")
            return 0.0


# Global reranker instance
reranker = CrossEncoderReranker()


def rerank_memories(query: str, memories: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for memory reranking"""
    return reranker.rerank_memories(query, memories, top_k)


def rerank_retrieval_results(query: str, retrieval_results: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for retrieval result reranking"""
    return reranker.rerank_retrieval_results(query, retrieval_results, top_k)
