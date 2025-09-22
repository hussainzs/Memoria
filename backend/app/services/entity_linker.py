"""
Entity linking service for connecting related entities across memories
"""
import re
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from ..db.models import Memory, Entity, MemoryLink


class EntityLinker:
    def __init__(self, db: Session):
        self.db = db
        self.entity_cache = {}
        self.similarity_threshold = 0.8

    def link_entities_in_memory(self, memory_id: str, entities: List[Dict[str, Any]], user_id: str) -> List[str]:
        """
        Link entities in a memory to existing entities or create new ones
        
        Args:
            memory_id: ID of the memory
            entities: List of extracted entities
            user_id: User ID for the entities
            
        Returns:
            List of linked entity IDs
        """
        linked_entity_ids = []
        
        for entity_data in entities:
            entity_name = entity_data['name']
            entity_type = entity_data['type']
            confidence = entity_data['confidence']
            
            entity = self._find_or_create_entity(entity_name, entity_type, user_id)
            if entity:
                linked_entity_ids.append(str(entity.id))
        
        return linked_entity_ids

    def _find_or_create_entity(self, name: str, entity_type: str, user_id: str) -> Entity:
        """Find existing entity or create new one"""
        normalized_name = self._normalize_entity_name(name)
        
        cache_key = f"{normalized_name}_{entity_type}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        existing_entity = self.db.query(Entity).filter(
            Entity.name.ilike(f"%{normalized_name}%"),
            Entity.type == entity_type
        ).first()
        
        if existing_entity:
            pass
            
            self.entity_cache[cache_key] = existing_entity
            return existing_entity
        
        new_entity = Entity(
            name=normalized_name,
            type=entity_type,
            user_id=user_id
        )
        
        self.db.add(new_entity)
        self.db.commit()
        self.db.refresh(new_entity)
        
        self.entity_cache[cache_key] = new_entity
        return new_entity

    def _normalize_entity_name(self, name: str) -> str:
        """Normalize entity name for consistent matching"""
        normalized = name.title()
        
        variations = {
            'Python': 'Python',
            'Javascript': 'JavaScript',
            'Javascript': 'JavaScript',
            'Postgresql': 'PostgreSQL',
            'Nodejs': 'Node.js',
            'Node.js': 'Node.js'
        }
        
        return variations.get(normalized, normalized)

    def _link_entity_to_memory(self, entity_id: str, memory_id: str, confidence: float):
        """Link an entity to a memory"""
        existing_link = self.db.query(MemoryLink).filter(
            MemoryLink.src_id == memory_id,
            MemoryLink.dst_id == entity_id,
            MemoryLink.relation == "mentions"
        ).first()
        
        if not existing_link:
            link = MemoryLink(
                src_id=memory_id,
                dst_id=entity_id,
                relation="mentions"
            )
            self.db.add(link)
            self.db.commit()

    def find_related_memories(self, entity_name: str, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find memories related to a specific entity
        
        Args:
            entity_name: Name of the entity to search for
            user_id: User ID to filter memories
            limit: Maximum number of memories to return
            
        Returns:
            List of related memories
        """
        entity = self.db.query(Entity).filter(
            Entity.name.ilike(f"%{entity_name}%"),
            Entity.user_id == user_id
        ).first()
        
        if not entity:
            return []
        
        related_memories = self.db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.entity_ids.contains([str(entity.id)])
        ).limit(limit).all()
        
        return [
            {
                'id': str(memory.id),
                'title': memory.title,
                'content': memory.content,
                'confidence': memory.confidence,
                'created_at': memory.created_at.isoformat()
            }
            for memory in related_memories
        ]

    def get_entity_graph(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get entity relationship graph for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of entities to return
            
        Returns:
            Entity graph with relationships
        """
        entity_counts = self.db.query(
            Entity.name,
            Entity.type,
            MemoryLink.src_id
        ).join(
            MemoryLink,
            Entity.id == MemoryLink.dst_id
        ).join(
            Memory,
            MemoryLink.src_id == Memory.id
        ).filter(
            Memory.user_id == user_id
        ).all()
        
        entity_freq = defaultdict(int)
        entities = {}
        
        for name, entity_type, memory_id in entity_counts:
            entity_freq[name] += 1
            if name not in entities:
                entities[name] = {
                    'name': name,
                    'type': entity_type,
                    'frequency': 0
                }
            entities[name]['frequency'] = entity_freq[name]
        
        top_entities = sorted(
            entities.values(),
            key=lambda x: x['frequency'],
            reverse=True
        )[:limit]
        
        return {
            'entities': top_entities,
            'total_entities': len(entities)
        }

    def suggest_related_entities(self, entity_name: str, user_id: str) -> List[Dict[str, Any]]:
        """
        Suggest entities related to a given entity
        
        Args:
            entity_name: Name of the entity
            user_id: User ID
            limit: Maximum number of suggestions
            
        Returns:
            List of related entity suggestions
        """
        memories = self.db.query(Memory).filter(
            Memory.user_id == user_id,
            Memory.content.ilike(f"%{entity_name}%")
        ).all()
        
        related_entities = set()
        for memory in memories:
            entities = self._extract_entities_from_text(memory.content)
            for entity in entities:
                if entity['name'].lower() != entity_name.lower():
                    related_entities.add(entity['name'])
        
        return [
            {'name': name, 'type': 'UNKNOWN', 'confidence': 0.5}
            for name in list(related_entities)[:10]
        ]

    def _extract_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Simple entity extraction for related entity suggestions"""
        entities = []
        
        proper_nouns = re.findall(r'\b[A-Z][a-z]+\b', text)
        for noun in proper_nouns:
            if len(noun) > 2:
                entities.append({
                    'name': noun,
                    'type': 'UNKNOWN',
                    'confidence': 0.5
                })
        
        return entities


def link_entities_in_memory(memory_id: str, entities: List[Dict[str, Any]], db: Session, user_id: str) -> List[str]:
    """Convenience function for linking entities in a memory"""
    linker = EntityLinker(db)
    return linker.link_entities_in_memory(memory_id, entities, user_id)


def find_related_memories(entity_name: str, user_id: str, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for finding related memories"""
    linker = EntityLinker(db)
    return linker.find_related_memories(entity_name, user_id, limit)
