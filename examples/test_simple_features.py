#!/usr/bin/env python3
"""Simple test of key features."""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def ingest_and_query():
    """Test basic ingestion and queries."""
    
    # Test 1: Vendor entity resolution
    print("1. Testing vendor entity resolution...")
    print("-" * 40)
    
    vendor_transcript = """
    Meeting: Vendor Discussion
    
    Alice: We have vendor issues with our cloud provider causing delays.
    Bob: I'll get vendor quotes for infrastructure to find alternatives.
    Carol: The vendor quotes for infrastructure should include support costs.
    """
    
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Vendor Discussion",
            "transcript": vendor_transcript
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Ingested successfully")
        print(f"  - Entities: {result.get('entity_count', 0)}")
        print(f"  - Memories: {result.get('memory_count', 0)}")
    else:
        print(f"✗ Failed: {response.text[:200]}")
        return
    
    time.sleep(1)
    
    # Query for vendor entities
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "List all vendor related items"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Query successful")
        print(f"Answer: {result.get('answer', '')[:300]}...")
        print(f"Entities involved: {len(result.get('entities_involved', []))}")
        for e in result.get('entities_involved', [])[:5]:
            print(f"  - {e.get('name')} ({e.get('type')})")
    
    # Test 2: State tracking
    print("\n\n2. Testing state tracking...")
    print("-" * 40)
    
    progress_transcript = """
    Meeting: Project Update
    
    David: The mobile app redesign project is now in progress, about 50% complete.
    Eve: The API optimization is blocked on database migration approval.
    Frank: I've completed the infrastructure audit. All systems are stable.
    """
    
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Project Update",
            "transcript": progress_transcript
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Ingested successfully")
        print(f"  - Entities: {result.get('entity_count', 0)}")
    else:
        print(f"✗ Failed: {response.text[:200]}")
    
    # Query for project status
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "What's the status of our projects?"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Status query successful")
        print(f"Answer: {result.get('answer', '')[:300]}...")
    
    # Test 3: Entity resolution variations
    print("\n\n3. Testing entity resolution...")
    print("-" * 40)
    
    queries = [
        "Tell me about the mobile app project",  # Should match "mobile app redesign project"
        "What's happening with API optimization", # Should match "API optimization"
        "Show me vendor quotes",  # Should match "vendor quotes for infrastructure"
    ]
    
    for query in queries:
        response = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": query}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\nQuery: {query}")
            print(f"Confidence: {result.get('confidence', 0):.2f}")
            metadata = result.get('metadata', {})
            if 'resolution_stats' in metadata:
                print(f"Resolution: {metadata['resolution_stats']}")

def main():
    print("=" * 60)
    print("SIMPLE FEATURE TEST")
    print("=" * 60)
    
    ingest_and_query()
    
    print("\n\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()