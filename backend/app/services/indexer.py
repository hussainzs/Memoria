import os
import re
from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
from .llm_client import LLMClient
from ..core.config import settings


class IndexResult:
    def __init__(
        self, 
        embedding: Optional[List[float]] = None, 
        summary: Optional[str] = None, 
        tags: Optional[List[str]] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        confidence: float = 0.5
    ):
        self.embedding = embedding
        self.summary = summary
        self.tags = tags or []
        self.entities = entities or []
        self.confidence = confidence


class TextIndexer:
    def __init__(self):
        self.embedding_model = None
        self.llm = LLMClient()
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize embedding and LLM models"""
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Loaded sentence transformer model")
        except Exception as e:
            print(f"Failed to load sentence transformer: {e}")
            self.embedding_model = None
        
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if not self.embedding_model:
            return None
        
        try:
            clean_text = self._clean_text(text)
            if len(clean_text) > 512:
                clean_text = clean_text[:512]
            
            embedding = self.embedding_model.encode(clean_text)
            return embedding.tolist()
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return None
    
    def generate_summary(self, content: str) -> str:
        """Generate a concise summary of the content"""
        if not (self.llm and self.llm.is_available()):
            return content[:160] + "..." if len(content) > 160 else content
        
        try:
            return self.llm.chat(
                messages=[
                    {"role": "system", "content": "Summarize the following text in 1-2 sentences:"},
                    {"role": "user", "content": content[:2000]},
                ],
                max_tokens=100,
                temperature=0.3,
            )
        except Exception as e:
            print(f"Error generating summary: {e}")
            return content[:160] + "..." if len(content) > 160 else content
    
    def extract_tags(self, content: str) -> List[str]:
        """Extract relevant tags from content"""
        tags = []
        
        tech_terms = re.findall(r'\b(python|javascript|docker|postgresql|redis|api|database|ml|ai|llm|vector|embedding)\b', 
                               content.lower())
        tags.extend(tech_terms)
        
        project_terms = re.findall(r'\b(project|meeting|development|code|system|architecture|design)\b', 
                                  content.lower())
        tags.extend(project_terms)
        
        preference_terms = re.findall(r'\b(prefer|like|favorite|usually|always|never|hate)\b', 
                                     content.lower())
        if preference_terms:
            tags.append('preference')
        
        skill_terms = re.findall(r'\b(experience|expertise|skill|knowledge|know|learned|mastered)\b', 
                                content.lower())
        if skill_terms:
            tags.append('skill')
        
        return list(set(tags))[:10]
    
    def extract_entities(self, content: str) -> List[Dict[str, Any]]:
        """Extract named entities from content with enhanced patterns"""
        entities = []
        
        tech_terms = re.findall(r'\b(Python|JavaScript|Java|C\+\+|Go|Rust|Docker|Kubernetes|PostgreSQL|Redis|MongoDB|MySQL|AWS|Azure|GCP|React|Vue|Angular|Node\.js|Django|Flask|FastAPI|Spring|Laravel)\b', content, re.IGNORECASE)
        for tech in tech_terms:
            entities.append({
                'name': tech.title(),
                'type': 'TECHNOLOGY',
                'confidence': 0.9
            })
        
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        for noun in proper_nouns:
            if len(noun) > 2 and noun not in ['The', 'This', 'That', 'These', 'Those']:
                entity_type = 'PERSON' if any(word in noun for word in ['Sarah', 'John', 'Mike', 'Alex']) else 'ORG'
                entities.append({
                    'name': noun,
                    'type': entity_type,
                    'confidence': 0.7
                })
        
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
        for email in emails:
            entities.append({
                'name': email,
                'type': 'EMAIL',
                'confidence': 0.9
            })
        
        urls = re.findall(r'https?://[^\s]+', content)
        for url in urls:
            entities.append({
                'name': url,
                'type': 'URL',
                'confidence': 0.9
            })
        
        dates = re.findall(r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b', content)
        for date in dates:
            entities.append({
                'name': date,
                'type': 'DATE',
                'confidence': 0.8
            })
        
        locations = re.findall(r'\b(New York|San Francisco|London|Paris|Tokyo|Berlin|Mumbai|Sydney|Toronto|Vancouver)\b', content, re.IGNORECASE)
        for location in locations:
            entities.append({
                'name': location.title(),
                'type': 'LOCATION',
                'confidence': 0.8
            })
        
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity['name'] not in seen:
                seen.add(entity['name'])
                unique_entities.append(entity)
        
        return unique_entities[:25]
    
    def _clean_text(self, text: str) -> str:
        """Clean text for processing"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s.,!?;:-]', '', text)
        return text.strip()
    
    def index_text(self, content: str, title: Optional[str] = None) -> IndexResult:
        """Main indexing function"""
        full_text = f"{title}: {content}" if title else content
        
        embedding = self.generate_embedding(full_text)
        
        summary = self.generate_summary(content)
        
        tags = self.extract_tags(full_text)
        
        entities = self.extract_entities(full_text)
        
        confidence = self._calculate_confidence(content, embedding, entities)
        
        return IndexResult(
            embedding=embedding,
            summary=summary,
            tags=tags,
            entities=entities,
            confidence=confidence
        )
    
    def _calculate_confidence(self, content: str, embedding: Optional[List[float]], entities: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for the indexed content"""
        confidence = 0.5
        
        if len(content) > 100:
            confidence += 0.1
        if len(content) > 500:
            confidence += 0.1
        
        if embedding:
            confidence += 0.2
        
        if entities:
            confidence += min(0.2, len(entities) * 0.05)
        
        if any(marker in content for marker in [':', '-', '•', '1.', '2.', '3.']):
            confidence += 0.1
        
        return min(1.0, confidence)


indexer = TextIndexer()


def index_text(content: str, title: Optional[str] = None) -> IndexResult:
    """Convenience function for text indexing"""
    return indexer.index_text(content, title)


