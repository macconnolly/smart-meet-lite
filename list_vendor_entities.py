#!/usr/bin/env python3
"""List all vendor-related entities to see the duplication."""

import sqlite3
from src.config import settings

conn = sqlite3.connect(settings.database_path)
cursor = conn.cursor()

# Get all entities with 'vendor' in the name
cursor.execute("""
    SELECT id, type, name, normalized_name, first_seen, last_updated
    FROM entities
    WHERE LOWER(name) LIKE '%vendor%'
    ORDER BY name
""")

entities = cursor.fetchall()

print(f"Found {len(entities)} vendor-related entities:\n")

# Group by similar names
groups = {}
for entity in entities:
    entity_id, entity_type, name, normalized_name, first_seen, last_updated = entity
    
    # Simple grouping by first few words
    key_words = name.lower().split()[:3]
    key = " ".join(key_words)
    
    if key not in groups:
        groups[key] = []
    
    groups[key].append({
        'id': entity_id,
        'type': entity_type,
        'name': name,
        'normalized_name': normalized_name,
        'first_seen': first_seen,
        'last_updated': last_updated
    })

# Show groups
for key, entities in groups.items():
    if len(entities) > 1:
        print(f"\nPotential duplicates for '{key}':")
        for e in entities:
            print(f"  - '{e['name']}' (type: {e['type']}, id: {e['id'][:8]}...)")
    else:
        e = entities[0]
        print(f"\nUnique: '{e['name']}' (type: {e['type']}, id: {e['id'][:8]}...)")

conn.close()