#!/usr/bin/env python3
"""Test that we don't get false positive matches."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

# First, let's check what vendor entities exist
print("Checking existing vendor entities...")
response = requests.post(
    f"{BASE_URL}/api/query",
    json={"query": "List all vendor entities"}
)

if response.status_code == 200:
    result = response.json()
    print(f"Answer: {result.get('answer', '')}")
    entities = result.get('entities_involved', [])
    vendor_entities = [e for e in entities if 'vendor' in e.get('name', '').lower()]
    print(f"\nVendor entities found: {len(vendor_entities)}")
    for e in vendor_entities:
        print(f"  - {e.get('name')} (id: {e.get('id')})")

# Now test a specific case
print("\n\nTesting entity resolution...")
test_transcript = """
Meeting: Test Resolution

Greg: We need vendor quotes for infrastructure upgrades.
Helen: Yes, get vendor quotes for infrastructure from three companies.
"""

response = requests.post(
    f"{BASE_URL}/api/ingest",
    json={
        "title": "Resolution Test",
        "transcript": test_transcript
    }
)

if response.status_code == 200:
    result = response.json()
    print("✓ Ingestion successful")
    
    # Query for relationships
    response = requests.post(
        f"{BASE_URL}/api/query", 
        json={"query": "Who is responsible for vendor quotes?"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Query successful")
        print(f"Answer: {result.get('answer', '')[:200]}...")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        
        # Check metadata
        metadata = result.get('metadata', {})
        if 'resolution_stats' in metadata:
            print(f"\nResolution stats: {metadata['resolution_stats']}")
            
        if 'low_confidence_terms' in metadata:
            print(f"Low confidence terms: {metadata['low_confidence_terms']}")