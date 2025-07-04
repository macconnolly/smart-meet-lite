#!/usr/bin/env python3
"""Test specific vendor entity resolution case."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_vendor_resolution():
    """Test that 'vendor quotes for infrastructure' doesn't match 'vendor issues'."""
    
    # First create vendor issues entity
    setup_transcript = """
    Meeting: Vendor Issues Discussion
    
    Alice: We have vendor issues with our cloud provider.
    Bob: Yes, the vendor issues are causing delays.
    Carol: I'll escalate the vendor issues to management.
    """
    
    print("1. Creating 'vendor issues' entity...")
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Vendor Issues Meeting",
            "transcript": setup_transcript
        }
    )
    
    if response.status_code != 200:
        print(f"✗ Setup failed: {response.text}")
        return False
    
    print("✓ Setup complete")
    
    # Now create vendor quotes entity  
    test_transcript = """
    Meeting: Infrastructure Planning
    
    David: I need vendor quotes for infrastructure upgrades.
    Eve: Please get three vendor quotes for infrastructure.
    Frank: The vendor quotes for infrastructure should include pricing.
    """
    
    print("\n2. Creating 'vendor quotes for infrastructure' entity...")
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Infrastructure Meeting",
            "transcript": test_transcript
        }
    )
    
    if response.status_code != 200:
        print(f"✗ Test ingestion failed: {response.text}")
        return False
        
    print("✓ Test ingestion complete")
    
    # Query for vendor entities
    print("\n3. Querying for vendor entities...")
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "List all vendor related entities"}
    )
    
    if response.status_code != 200:
        print(f"✗ Query failed: {response.text}")
        return False
        
    result = response.json()
    print(f"✓ Query complete")
    print(f"Answer: {result.get('answer', '')}")
    
    # Check entities involved
    entities = result.get('entities_involved', [])
    vendor_entities = [e for e in entities if 'vendor' in e.get('name', '').lower()]
    
    print(f"\nVendor entities found: {len(vendor_entities)}")
    for entity in vendor_entities:
        print(f"  - {entity.get('name')} (type: {entity.get('type')})")
    
    # Test specific query for vendor quotes
    print("\n4. Testing specific query for vendor quotes...")
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "Who needs vendor quotes for infrastructure?"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Specific query complete")
        print(f"Answer: {result.get('answer', '')[:200]}...")
        print(f"Confidence: {result.get('confidence', 0):.2f}")
        
        # Check resolution metadata
        metadata = result.get('metadata', {})
        if 'resolution_stats' in metadata:
            print(f"Resolution stats: {metadata['resolution_stats']}")
    
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("VENDOR ENTITY RESOLUTION TEST")
    print("=" * 60)
    
    try:
        # Check API is running
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("✗ API is not running")
            exit(1)
            
        if test_vendor_resolution():
            print("\n✓ Test completed successfully!")
        else:
            print("\n✗ Test failed!")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")