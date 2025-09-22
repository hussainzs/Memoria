import json
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from .retriever import HybridRetriever, retrieve_hybrid
from .reranker import rerank_retrieval_results
from .indexer import index_text
from .temporal_scorer import update_recall_stats
from .verifier import verify_answer
from ..core.config import settings
from .llm_client import LLMClient


class OrchestrationResult:
    def __init__(self, answer: str, citations: List[Dict[str, Any]], confidence: float, sources: List[str]):
        self.answer = answer
        self.citations = citations
        self.confidence = confidence
        self.sources = sources


class MemoryOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.retriever = HybridRetriever(db)
        self.llm = LLMClient()
    
    def _initialize_llm(self):
        pass
    
    def ask_question(
        self, 
        question: str, 
        user_id: str, 
        max_memories: int = 8,
        include_verification: bool = True
    ) -> OrchestrationResult:
        """
        Main orchestration pipeline:
        1. Query rewrite/intent extraction
        2. Hybrid retrieval
        3. Cross-encoder reranking (placeholder)
        4. LLM grounding and answer generation
        5. Post-generation verification
        """
        
        intent = self._extract_intent(question)
        
        retrieval_results_primary = retrieve_hybrid(
            query=question,
            user_id=user_id,
            db=self.db,
            k=max_memories
        )
        
        additional_results: List[Dict[str, Any]] = []
        
        rewritten_keywords = self._rewrite_query_to_keywords(question)
        if rewritten_keywords and rewritten_keywords.lower() != question.lower():
            additional_results.extend(
                retrieve_hybrid(
                    query=rewritten_keywords,
                    user_id=user_id,
                    db=self.db,
                    k=max_memories
                )
            )
        
        if intent.get("entities"):
            try:
                entity_results = self.retriever.search_by_entities(intent["entities"], user_id, k=max_memories)
                additional_results.extend([
                    {
                        "id": r.memory_id,
                        "title": r.memory.title,
                        "content": r.memory.content,
                        "score": r.score,
                        "method": r.retrieval_method,
                        "created_at": r.memory.created_at.isoformat(),
                        "recall_count": r.memory.recall_count,
                        "confidence": r.memory.confidence,
                    }
                    for r in entity_results
                ])
            except Exception as e:
                print(f"Entity retrieval error: {e}")
        
        retrieval_results = self._merge_results_by_id(retrieval_results_primary + additional_results)
        
        retrieved_memories = []
        for result in retrieval_results:
            from ..db.models import Memory
            from uuid import UUID
            memory_uuid = UUID(result["id"]) if isinstance(result["id"], str) else result["id"]
            memory = self.db.query(Memory).filter(Memory.id == memory_uuid).first()
            if memory:
                from .retriever import RetrievalResult
                retrieved_memories.append(RetrievalResult(
                    memory_id=result["id"],
                    score=result["score"],
                    memory=memory,
                    retrieval_method=result["method"]
                ))
        
        if not retrieved_memories:
            return OrchestrationResult(
                answer="I don't have any relevant memories to answer your question.",
                citations=[],
                confidence=0.0,
                sources=[]
            )
        
        
        retrieval_results = []
        for mem in retrieved_memories:
            retrieval_results.append({
                'id': mem.memory_id,
                'title': mem.memory.title or '',
                'content': mem.memory.content,
                'score': mem.score,
                'method': mem.retrieval_method
            })
        
        reranked_results = rerank_retrieval_results(question, retrieval_results, max_memories)
        
        reranked_memories = []
        for result in reranked_results:
            from ..db.models import Memory
            from uuid import UUID
            memory_uuid = UUID(result["id"]) if isinstance(result["id"], str) else result["id"]
            memory = self.db.query(Memory).filter(Memory.id == memory_uuid).first()
            if memory:
                from .retriever import RetrievalResult
                reranked_memories.append(RetrievalResult(
                    memory_id=result["id"],
                    score=result["score"],
                    memory=memory,
                    retrieval_method=result["method"]
                ))
        
        prompt = self._construct_grounded_prompt(question, reranked_memories, intent)
        
        if self.llm and self.llm.is_available():
            answer_result = self._generate_answer_with_llm(prompt, question)
        else:
            answer_result = self._generate_fallback_answer(question, reranked_memories)
        
        if include_verification and self.llm and self.llm.is_available():
            verified_result = self._verify_answer(answer_result, reranked_memories)
        else:
            verified_result = answer_result
        
        self._update_recall_counts([mem.memory_id for mem in reranked_memories])
        
        return verified_result
    
    def _extract_intent(self, question: str) -> Dict[str, Any]:
        """Extract intent, entities, and temporal constraints from question"""
        if not (self.llm and self.llm.is_available()):
            return {"intent": "general_query", "entities": [], "temporal": None}
        
        try:
            completion = self.llm.chat(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Extract intent, entities, and temporal constraints from the user question. "
                            "Return ONLY valid minified JSON object with keys intent (string), entities (array of strings), temporal (string|null). "
                            "No explanations, no code fences."
                        ),
                    },
                    {"role": "user", "content": f"Question: {question}"},
                ],
                max_tokens=200,
                temperature=0.1,
            )
            try:
                return json.loads(completion)
            except Exception:
                import re
                match = re.search(r"\{[\s\S]*\}", completion)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except Exception:
                        pass
                return {"intent": "general_query", "entities": [], "temporal": None}
        except Exception as e:
            print(f"Intent extraction error: {e}")
            return {"intent": "general_query", "entities": [], "temporal": None}
    
    
    def _construct_grounded_prompt(
        self, 
        question: str, 
        memories: List, 
        intent: Dict[str, Any]
    ) -> str:
        """Construct a grounded prompt with memory citations"""
        
        memory_contexts = []
        for i, memory in enumerate(memories, 1):
            memory_text = f"[MEMORY_{i}: {memory.memory_id}]\n"
            if memory.memory.title:
                memory_text += f"Title: {memory.memory.title}\n"
            memory_text += f"Content: {memory.memory.content}\n"
            memory_text += f"Confidence: {memory.memory.confidence:.2f}\n"
            memory_contexts.append(memory_text)
        
        context_text = "\n\n".join(memory_contexts)
        
        prompt = f"""You are a careful assistant with access to the user's personal memories. Use ONLY the provided memories as evidence to answer the question.

MEMORIES:
{context_text}

QUESTION: {question}

INSTRUCTIONS:
1. Answer based ONLY on the provided memories
2. Cite memory IDs using [MEMORY_X] format
3. If no relevant memory exists, say "I don't have information about this in my memories"
4. Be concise and accurate
5. If uncertain, express your uncertainty

ANSWER:"""
        
        return prompt

    def _rewrite_query_to_keywords(self, question: str) -> Optional[str]:
        """Rewrite a potentially long/complex question to concise keyword query.
        Uses LLM if available; falls back to simple heuristic keyword extraction.
        """
        try:
            if self.llm and self.llm.is_available():
                completion = self.llm.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Rewrite the user's question into a concise list of search keywords (3-8). "
                                "Return ONLY the keywords separated by spaces. No punctuation or explanations."
                            ),
                        },
                        {"role": "user", "content": question},
                    ],
                    max_tokens=60,
                    temperature=0.0,
                )
                return completion.strip()
        except Exception as e:
            print(f"Keyword rewrite error: {e}")
        
        # Heuristic fallback: keep alnum tokens > 3 chars, dedupe, cap length
        import re
        tokens = re.findall(r"[A-Za-z0-9]+", question)
        keywords = []
        seen = set()
        for t in tokens:
            lt = t.lower()
            if len(lt) > 3 and lt not in seen:
                seen.add(lt)
                keywords.append(lt)
            if len(keywords) >= 8:
                break
        return " ".join(keywords)

    def _merge_results_by_id(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge retrieval results keeping the highest score per memory id."""
        merged: Dict[str, Dict[str, Any]] = {}
        for r in results:
            rid = r.get("id")
            if not rid:
                continue
            if rid not in merged or (r.get("score", 0.0) > merged[rid].get("score", 0.0)):
                merged[rid] = r
        return list(merged.values())
    
    def _generate_answer_with_llm(self, prompt: str, original_question: str) -> OrchestrationResult:
        """Generate answer using LLM"""
        try:
            answer = self.llm.chat(
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided memories. Always cite your sources."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            
            citations = self._extract_citations_from_answer(answer)
            
            return OrchestrationResult(
                answer=answer,
                citations=citations,
                confidence=0.8,
                sources=[citation["memory_id"] for citation in citations]
            )
        except Exception as e:
            print(f"LLM generation error: {e}")
            return self._generate_fallback_answer(original_question, [])
    
    def _generate_fallback_answer(self, question: str, memories: List) -> OrchestrationResult:
        """Generate fallback answer without LLM"""
        if not memories:
            return OrchestrationResult(
                answer="I don't have any relevant memories to answer your question.",
                citations=[],
                confidence=0.0,
                sources=[]
            )
        
        best_memory = memories[0]
        answer = f"Based on my memories: {best_memory.memory.content}"
        
        return OrchestrationResult(
            answer=answer,
            citations=[{"memory_id": best_memory.memory_id, "confidence": best_memory.score}],
            confidence=0.5,
            sources=[best_memory.memory_id]
        )
    
    def _extract_citations_from_answer(self, answer: str) -> List[Dict[str, Any]]:
        """Extract memory citations from the answer"""
        import re
        citations = []
        
        memory_pattern = r'\[MEMORY_(\d+)\]'
        matches = re.findall(memory_pattern, answer)
        
        for match in matches:
            citations.append({
                "memory_id": f"memory_{match}",
                "confidence": 0.8
            })
        
        return citations
    
    def _verify_answer(self, result: OrchestrationResult, memories: List) -> OrchestrationResult:
        """Enhanced post-generation verification using verifier service"""
        try:
            memory_objects = [mem.memory for mem in memories]
            
            verification_result = verify_answer(
                answer=result.answer,
                memories=memory_objects,
                question="Generated answer"
            )
            
            result.confidence = verification_result.confidence
            
            if not hasattr(result, 'verification'):
                result.verification = {}
            
            result.verification = {
                'is_verified': verification_result.is_verified,
                'fact_check_score': verification_result.fact_check_score,
                'citation_score': verification_result.citation_score,
                'consistency_score': verification_result.consistency_score,
                'issues': verification_result.issues,
                'suggestions': verification_result.suggestions
            }
            
        except Exception as e:
            print(f"Verification error: {e}")
            if not hasattr(result, 'verification'):
                result.verification = {
                    'is_verified': False,
                    'error': str(e)
                }
        
        return result
    
    def _update_recall_counts(self, memory_ids: List[str]):
        """Update recall counts for accessed memories using temporal scorer"""
        try:
            from ..db.models import Memory
            
            memories = self.db.query(Memory).filter(Memory.id.in_(memory_ids)).all()
            
            for memory in memories:
                update_recall_stats(memory, self.db)
                
        except Exception as e:
            print(f"Error updating recall counts: {e}")


def run_orchestration(question: str, user_id: str, db: Session) -> Dict[str, Any]:
    """Convenience function for orchestration"""
    orchestrator = MemoryOrchestrator(db)
    result = orchestrator.ask_question(question, user_id)
    
    return {
        "answer": result.answer,
        "citations": result.citations,
        "confidence": result.confidence,
        "sources": result.sources
    }


