#!/usr/bin/env python3
"""Investigate why entities aren't being created."""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def check_entities():
    """Check all entities in the system."""
    response = requests.get(f"{BASE_URL}/api/entities")
    if response.status_code == 200:
        entities = response.json()
        print(f"\nTotal entities in system: {len(entities)}")
        
        # Group by type
        by_type = {}
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity)
        
        for entity_type, entities_list in by_type.items():
            print(f"\n{entity_type.upper()} entities ({len(entities_list)}):")
            for e in entities_list[:5]:  # Show first 5 of each type
                print(f"  - {e.get('name')} (id: {e.get('id')[:8]}...)")
            if len(entities_list) > 5:
                print(f"  ... and {len(entities_list) - 5} more")
    else:
        print(f"Failed to get entities: {response.status_code}")

def test_new_entity_creation():
    """Test creating brand new entities."""
    
    # Use a unique entity name that definitely doesn't exist
    unique_name = f"TestProject_{int(time.time())}"
    
    transcript = f"""
    Meeting: Entity Creation Test
    
    Alice: Let's discuss the {unique_name}.
    Bob: The {unique_name} is making good progress.
    Carol: I think {unique_name} needs more resources.
    
    Decision: We've decided to allocate more budget to {unique_name}.
    
    Action Item: Alice will create a timeline for {unique_name} by next week.
    """
    
    print(f"\n\nTesting entity creation with unique name: {unique_name}")
    
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Entity Creation Test",
            "transcript": transcript
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Ingestion successful")
        print(f"  - Entities created: {result.get('entity_count', 0)}")
        print(f"  - Processing results available: {'processing_results' in result}")
        
        # Check if our unique entity was created
        response = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": f"What is the status of {unique_name}?"}
        )
        
        if response.status_code == 200:
            query_result = response.json()
            print(f"\n✓ Query for {unique_name}:")
            print(f"  Answer: {query_result.get('answer', '')[:150]}...")
            print(f"  Confidence: {query_result.get('confidence', 0):.2f}")
            
            # Check entities involved
            entities_involved = query_result.get('entities_involved', [])
            print(f"  Entities involved: {len(entities_involved)}")
            for e in entities_involved:
                print(f"    - {e.get('name')} (type: {e.get('type')})")
    else:
        print(f"✗ Ingestion failed: {response.status_code}")
        print(response.text)

def test_extraction_directly():
    """Test the extraction endpoint if it exists."""
    
    transcript = """
    Meeting: Direct Extraction Test
    
    Participants: Alice, Bob, Carol
    
    Alice: We need to start the Mobile App Redesign project.
    Bob: I'll lead the Backend API Optimization.
    Carol: The Customer Dashboard needs updating.
    
    Decisions:
    - We've decided to use React Native for the mobile app
    - Budget approved for hiring two developers
    
    Action Items:
    - Alice will create wireframes for the mobile app
    - Bob will document the API requirements
    - Carol will gather customer feedback
    """
    
    print("\n\nTesting extraction results...")
    
    # First ingest
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Direct Extraction Test",
            "transcript": transcript
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✓ Ingestion response:")
        print(f"  - Meeting ID: {result.get('id', 'N/A')}")
        print(f"  - Title: {result.get('title', 'N/A')}")
        print(f"  - Participants: {result.get('participants', [])}")
        print(f"  - Topics: {result.get('topics', [])}")
        print(f"  - Decisions: {len(result.get('decisions', []))}")
        print(f"  - Action items: {len(result.get('action_items', []))}")
        print(f"  - Memory count: {result.get('memory_count', 0)}")
        print(f"  - Entity count: {result.get('entity_count', 0)}")
        
        # Show action items
        action_items = result.get('action_items', [])
        if action_items:
            print("\n  Action items extracted:")
            for item in action_items:
                print(f"    - {item}")

def main():
    print("=" * 60)
    print("ENTITY CREATION INVESTIGATION")
    print("=" * 60)
    
    # Check API
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("✗ API is not running")
            return
    except:
        print("✗ Cannot connect to API")
        return
    
    # Check current entities
    check_entities()
    
    # Test new entity creation
    test_new_entity_creation()
    
    # Test extraction
    test_extraction_directly()
    
    # Check entities again
    print("\n\nFinal entity check:")
    check_entities()

if __name__ == "__main__":
    main()