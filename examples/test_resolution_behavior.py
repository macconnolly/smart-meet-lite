#!/usr/bin/env python3
"""Test entity resolution behavior in detail."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Test 1: Check if "vendor quotes for infrastructure" exists
print("1. Checking existing vendor entities...")
response = requests.post(
    f"{BASE_URL}/api/query",
    json={"query": "Show me all vendor related entities"}
)

if response.status_code == 200:
    result = response.json()
    entities = result.get('entities_involved', [])
    print(f"Found {len(entities)} vendor-related entities:")
    for e in entities:
        if 'vendor' in e.get('name', '').lower():
            print(f"  - '{e.get('name')}' (type: {e.get('type')}, id: {e.get('id')[:8]}...)")

# Test 2: Try to create a duplicate
print("\n2. Testing duplicate entity creation...")
transcript = """
Alice: We need vendor quotes for infrastructure upgrades.
Bob: The vendor quotes for infrastructure should include pricing.
"""

response = requests.post(
    f"{BASE_URL}/api/ingest",
    json={
        "title": "Duplicate Test",
        "transcript": transcript
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"✓ Ingestion complete:")
    print(f"  - New entities created: {result.get('entity_count', 0)}")
    print(f"  - Total memories: {result.get('memory_count', 0)}")

# Test 3: Check resolution stats
print("\n3. Checking entity resolution stats...")
response = requests.get(f"{BASE_URL}/api/stats/entity-resolution")
if response.status_code == 404:
    print("  Resolution stats endpoint not available")
else:
    print(f"  Response: {response.status_code}")

# Test 4: Create a genuinely new entity
unique_name = f"UniqueVendor_{int(time.time())}"
print(f"\n4. Creating genuinely new entity: {unique_name}")
transcript = f"""
Carol: We need to contact {unique_name} for quotes.
David: {unique_name} has the best prices in the market.
"""

response = requests.post(
    f"{BASE_URL}/api/ingest",
    json={
        "title": "New Entity Test",
        "transcript": transcript
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"✓ Ingestion complete:")
    print(f"  - New entities created: {result.get('entity_count', 0)}")
    
    # Verify it was created
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": f"Tell me about {unique_name}"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n  Query result:")
        print(f"  - Answer: {result.get('answer', '')[:100]}...")
        print(f"  - Confidence: {result.get('confidence', 0):.2f}")
        entities = result.get('entities_involved', [])
        for e in entities:
            if unique_name.lower() in e.get('name', '').lower():
                print(f"  ✓ Found entity: '{e.get('name')}' (type: {e.get('type')})")

# Test 5: Check fuzzy matching
print("\n5. Testing fuzzy matching...")
transcript = """
Eve: The vendor quotes for the infrastructure project are ready.
Frank: Good, the infrastructure vendor quotes look reasonable.
"""

response = requests.post(
    f"{BASE_URL}/api/ingest",
    json={
        "title": "Fuzzy Match Test",
        "transcript": transcript
    }
)

if response.status_code == 200:
    result = response.json()
    print(f"✓ Ingestion complete:")
    print(f"  - New entities created: {result.get('entity_count', 0)}")
    print("  - Should be 0 if fuzzy matching worked correctly")