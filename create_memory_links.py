#!/usr/bin/env python3
"""
Script to create memory links for testing the graph visualization.
This will create relationships between existing memories.
"""

import requests
import json
import random
from datetime import datetime, timedelta

# Configuration
API_BASE = "http://localhost:8000"
USER_ID = "user-001"  # Use the same user ID as our sample data

# Sample relationships to create
RELATIONSHIPS = [
    ("relates_to", "Memory about Memoria project relates to memory about long-term memory systems"),
    ("builds_on", "Memory about vector embeddings builds on memory about database design"),
    ("contradicts", "Memory about simple approach contradicts memory about complex systems"),
    ("supports", "Memory about user experience supports memory about frontend design"),
    ("extends", "Memory about backend services extends memory about API design"),
    ("references", "Memory about testing references memory about sample data"),
    ("implements", "Memory about Docker setup implements memory about containerization"),
    ("optimizes", "Memory about performance optimizes memory about system architecture"),
    ("depends_on", "Memory about frontend depends on memory about backend API"),
    ("enhances", "Memory about verification enhances memory about accuracy")
]

def get_memories():
    """Get all memories for the user"""
    try:
        response = requests.get(f"{API_BASE}/memories/?user_id={USER_ID}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching memories: {e}")
        return []

def create_memory_link(src_id, dst_id, relation):
    """Create a memory link using the API endpoint"""
    link_data = {
        "src_id": src_id,
        "dst_id": dst_id,
        "relation": relation
    }
    
    try:
        response = requests.post(f"{API_BASE}/memories/links", json=link_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error creating memory link: {e}")
        return None

def main():
    print("🔗 Creating memory links for graph visualization...")
    
    # Get existing memories
    memories = get_memories()
    if len(memories) < 2:
        print("❌ Need at least 2 memories to create links")
        return
    
    print(f"📚 Found {len(memories)} memories")
    
    # Create some random relationships
    created_links = 0
    for i in range(min(10, len(memories) // 2)):  # Create up to 10 links
        # Pick two random memories
        src_memory = random.choice(memories)
        dst_memory = random.choice([m for m in memories if m['id'] != src_memory['id']])
        relation = random.choice(RELATIONSHIPS)
        
        print(f"🔗 Creating link: {src_memory['title'][:30]}... -> {dst_memory['title'][:30]}... ({relation[0]})")
        
        # Create a link memory
        link_memory = create_memory_link(src_memory['id'], dst_memory['id'], relation[0])
        if link_memory:
            created_links += 1
    
    print(f"✅ Created {created_links} memory links")
    print(f"🌐 You can now view the graph at: http://localhost:3000/graph")
    print(f"👤 Use User ID: {USER_ID}")

if __name__ == "__main__":
    main()
