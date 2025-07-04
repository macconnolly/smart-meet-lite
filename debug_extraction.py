#!/usr/bin/env python3
"""Debug entity extraction behavior."""

import sys
sys.path.append('.')

from src.extractor import MemoryExtractor
from src.models import Meeting
from datetime import datetime

# Test the extractor directly
extractor = MemoryExtractor()

# Test 1: Simple vendor quotes
print("Test 1: Simple extraction")
print("-" * 50)
transcript1 = """
Alice: We need vendor quotes for infrastructure upgrades.
Bob: The vendor quotes for infrastructure should include pricing.
"""

extraction1 = extractor.extract(transcript1, "test1")
print("Entities extracted:")
for entity in extraction1.entities:
    print(f"  - '{entity.name}' (type: {entity.type})")

# Test 2: Different phrasing
print("\n\nTest 2: Different phrasing")
print("-" * 50)
transcript2 = """
Carol: The vendor quotes for the infrastructure project are ready.
David: Good, the infrastructure vendor quotes look reasonable.
"""

extraction2 = extractor.extract(transcript2, "test2")
print("Entities extracted:")
for entity in extraction2.entities:
    print(f"  - '{entity.name}' (type: {entity.type})")

# Test 3: Existing entity reference
print("\n\nTest 3: Existing entity reference")
print("-" * 50)
transcript3 = """
Eve: What's the status of vendor quotes for infrastructure?
Frank: The vendor quotes for infrastructure are still pending.
"""

extraction3 = extractor.extract(transcript3, "test3")
print("Entities extracted:")
for entity in extraction3.entities:
    print(f"  - '{entity.name}' (type: {entity.type})")

# Show relationships too
print("\n\nRelationships from Test 1:")
for rel in extraction1.relationships:
    print(f"  - {rel.get('from')} -> {rel.get('to')} ({rel.get('type')})")