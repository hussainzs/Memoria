"""
Verifier service for hallucination detection and answer verification
"""
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from ..db.models import Memory
from ..core.config import settings
from .llm_client import LLMClient


@dataclass
class VerificationResult:
    """Result of answer verification"""
    is_verified: bool
    confidence: float
    issues: List[str]
    suggestions: List[str]
    fact_check_score: float
    citation_score: float
    consistency_score: float


class AnswerVerifier:
    def __init__(self):
        self.llm = LLMClient()
        self._initialize_llm()
    
    def _initialize_llm(self):
        pass
    
    def verify_answer(
        self, 
        answer: str, 
        memories: List[Memory], 
        question: str
    ) -> VerificationResult:
        """
        Verify an answer against retrieved memories
        
        Args:
            answer: The generated answer to verify
            memories: List of retrieved memories used for grounding
            question: The original question
            
        Returns:
            VerificationResult with verification details
        """
        if not (self.llm and self.llm.is_available()):
            return self._fallback_verification(answer, memories, question)
        
        try:
            claims = self._extract_claims(answer)
            
            fact_check_result = self._fact_check_claims(claims, memories)
            
            citation_result = self._check_citations(answer, memories)
            
            consistency_result = self._check_consistency(answer)
            
            overall_confidence = self._calculate_overall_confidence(
                fact_check_result, citation_result, consistency_result
            )
            
            is_verified = overall_confidence >= 0.7
            
            issues, suggestions = self._generate_feedback(
                fact_check_result, citation_result, consistency_result
            )
            
            return VerificationResult(
                is_verified=is_verified,
                confidence=overall_confidence,
                issues=issues,
                suggestions=suggestions,
                fact_check_score=fact_check_result['score'],
                citation_score=citation_result['score'],
                consistency_score=consistency_result['score']
            )
            
        except Exception as e:
            print(f"Error in verification: {e}")
            return self._fallback_verification(answer, memories, question)
    
    def _extract_claims(self, answer: str) -> List[str]:
        """Extract factual claims from the answer"""
        if not (self.llm and self.llm.is_available()):
            return self._simple_claim_extraction(answer)
        
        try:
            prompt = f"""
            Extract factual claims from the following answer. Return only the claims as a JSON list of strings.
            Focus on specific, verifiable statements.
            
            Answer: {answer}
            
            Return format: ["claim1", "claim2", "claim3"]
            """
            
            claims_text = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.1,
            )
            try:
                claims = json.loads(claims_text)
                return claims if isinstance(claims, list) else [claims_text]
            except json.JSONDecodeError:
                return self._simple_claim_extraction(answer)
                
        except Exception as e:
            print(f"Error extracting claims: {e}")
            return self._simple_claim_extraction(answer)
    
    def _simple_claim_extraction(self, answer: str) -> List[str]:
        """Simple rule-based claim extraction"""
        sentences = re.split(r'[.!?]+', answer)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:
                if any(word in sentence.lower() for word in ['is', 'are', 'has', 'have', 'can', 'will', 'do', 'does']):
                    claims.append(sentence)
        
        return claims[:5]
    
    def _fact_check_claims(self, claims: List[str], memories: List[Memory]) -> Dict[str, Any]:
        """Fact check claims against retrieved memories"""
        if not claims or not memories:
            return {'score': 0.5, 'details': 'No claims or memories to check'}
        
        if not (self.llm and self.llm.is_available()):
            return self._simple_fact_check(claims, memories)
        
        try:
            memory_context = "\n".join([
                f"Memory {i+1}: {memory.content}" 
                for i, memory in enumerate(memories[:5])
            ])
            
            verified_claims = 0
            total_claims = len(claims)
            
            for claim in claims:
                prompt = f"""
                Verify if the following claim is supported by the provided memories.
                Answer with only "SUPPORTED" or "NOT_SUPPORTED" followed by a brief explanation.
                
                Claim: {claim}
                
                Memories:
                {memory_context}
                """
                
                result = self.llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=100,
                    temperature=0.1,
                )
                if "SUPPORTED" in result.upper():
                    verified_claims += 1
            
            score = verified_claims / total_claims if total_claims > 0 else 0.5
            
            return {
                'score': score,
                'verified_claims': verified_claims,
                'total_claims': total_claims,
                'details': f"Verified {verified_claims}/{total_claims} claims"
            }
            
        except Exception as e:
            print(f"Error in fact checking: {e}")
            return self._simple_fact_check(claims, memories)
    
    def _simple_fact_check(self, claims: List[str], memories: List[Memory]) -> Dict[str, Any]:
        """Simple rule-based fact checking"""
        memory_text = " ".join([memory.content.lower() for memory in memories])
        verified_claims = 0
        
        for claim in claims:
            claim_lower = claim.lower()
            claim_words = set(re.findall(r'\b\w+\b', claim_lower))
            memory_words = set(re.findall(r'\b\w+\b', memory_text))
            
            overlap = len(claim_words.intersection(memory_words))
            if overlap >= len(claim_words) * 0.3:
                verified_claims += 1
        
        score = verified_claims / len(claims) if claims else 0.5
        
        return {
            'score': score,
            'verified_claims': verified_claims,
            'total_claims': len(claims),
            'details': f"Simple verification: {verified_claims}/{len(claims)} claims"
        }
    
    def _check_citations(self, answer: str, memories: List[Memory]) -> Dict[str, Any]:
        """Check if citations properly support the answer"""
        if not memories:
            return {'score': 0.0, 'details': 'No memories to cite'}
        
        memory_details = []
        for memory in memories:
            details = memory.content[:100].lower()
            memory_details.append(details)
        
        answer_lower = answer.lower()
        cited_details = 0
        
        for detail in memory_details:
            detail_words = set(re.findall(r'\b\w+\b', detail))
            answer_words = set(re.findall(r'\b\w+\b', answer_lower))
            
            overlap = len(detail_words.intersection(answer_words))
            if overlap >= len(detail_words) * 0.2:
                cited_details += 1
        
        score = cited_details / len(memories) if memories else 0.0
        
        return {
            'score': score,
            'cited_memories': cited_details,
            'total_memories': len(memories),
            'details': f"Cited {cited_details}/{len(memories)} memories"
        }
    
    def _check_consistency(self, answer: str) -> Dict[str, Any]:
        """Check for internal consistency in the answer"""
        if not (self.llm and self.llm.is_available()):
            return self._simple_consistency_check(answer)
        
        try:
            prompt = f"""
            Check the following answer for internal consistency and contradictions.
            Look for conflicting statements, logical inconsistencies, or contradictory claims.
            Answer with only "CONSISTENT" or "INCONSISTENT" followed by a brief explanation.
            
            Answer: {answer}
            """
            
            result = self.llm.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.1,
            )
            is_consistent = "CONSISTENT" in result.upper()
            score = 1.0 if is_consistent else 0.0
            
            return {
                'score': score,
                'is_consistent': is_consistent,
                'details': result
            }
            
        except Exception as e:
            print(f"Error in consistency check: {e}")
            return self._simple_consistency_check(answer)
    
    def _simple_consistency_check(self, answer: str) -> Dict[str, Any]:
        """Simple rule-based consistency checking"""
        contradictions = [
            ("is", "is not"),
            ("are", "are not"),
            ("can", "cannot"),
            ("will", "will not"),
            ("always", "never"),
            ("all", "none")
        ]
        
        answer_lower = answer.lower()
        issues = 0
        
        for positive, negative in contradictions:
            if positive in answer_lower and negative in answer_lower:
                issues += 1
        
        score = max(0.0, 1.0 - (issues * 0.2))
        
        return {
            'score': score,
            'is_consistent': issues == 0,
            'details': f"Found {issues} potential contradictions"
        }
    
    def _calculate_overall_confidence(
        self, 
        fact_check: Dict[str, Any], 
        citation: Dict[str, Any], 
        consistency: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score"""
        weights = {
            'fact_check': 0.5,
            'citation': 0.3,
            'consistency': 0.2
        }
        
        overall_score = (
            weights['fact_check'] * fact_check['score'] +
            weights['citation'] * citation['score'] +
            weights['consistency'] * consistency['score']
        )
        
        return min(1.0, max(0.0, overall_score))
    
    def _generate_feedback(
        self, 
        fact_check: Dict[str, Any], 
        citation: Dict[str, Any], 
        consistency: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """Generate issues and suggestions based on verification results"""
        issues = []
        suggestions = []
        
        if fact_check['score'] < 0.7:
            issues.append(f"Low fact verification: {fact_check['details']}")
            suggestions.append("Verify claims against retrieved memories")
        
        if citation['score'] < 0.5:
            issues.append(f"Poor citation quality: {citation['details']}")
            suggestions.append("Ensure answer is properly grounded in retrieved memories")
        
        if consistency['score'] < 0.8:
            issues.append(f"Consistency issues: {consistency['details']}")
            suggestions.append("Review answer for internal contradictions")
        
        return issues, suggestions
    
    def _fallback_verification(self, answer: str, memories: List[Memory], question: str) -> VerificationResult:
        """Fallback verification when LLM is not available"""
        fact_check = self._simple_fact_check([answer], memories)
        citation = self._check_citations(answer, memories)
        consistency = self._simple_consistency_check(answer)
        
        overall_confidence = self._calculate_overall_confidence(fact_check, citation, consistency)
        
        return VerificationResult(
            is_verified=overall_confidence >= 0.6,
            confidence=overall_confidence,
            issues=[] if overall_confidence >= 0.6 else ["Limited verification available"],
            suggestions=["Enable LLM verification for enhanced checking"],
            fact_check_score=fact_check['score'],
            citation_score=citation['score'],
            consistency_score=consistency['score']
        )


verifier = AnswerVerifier()


def verify_answer(answer: str, memories: List[Memory], question: str) -> VerificationResult:
    """Convenience function for answer verification"""
    return verifier.verify_answer(answer, memories, question)

