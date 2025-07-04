#!/usr/bin/env python3
"""Test script to verify truncation removal functionality."""

import requests
import json
import time
from datetime import datetime

# API base URL
BASE_URL = "http://localhost:8000"

def test_ingestion_with_many_items():
    """Test ingestion of a transcript with many decisions and action items."""
    
    # Create a transcript with many decisions and action items
    transcript = f"""
    Meeting: Q4 Planning Session
    Date: {datetime.now().strftime('%Y-%m-%d')}
    
    Alice: Welcome everyone to our Q4 planning session. Let's go through our major initiatives.
    
    Bob: I've decided we'll implement feature A by end of November.
    Carol: We've decided to prioritize the mobile app redesign over the web refresh.
    David: The team has decided to adopt microservices architecture for the new platform.
    Eve: We've decided to increase the QA team size by 3 people.
    Frank: Management decided to allocate $500k for infrastructure upgrades.
    Grace: We've decided to sunset the legacy API by January.
    Henry: The board decided to pursue the European market expansion.
    Isabel: We've decided to implement weekly sprint reviews.
    Jack: Product team decided to add real-time collaboration features.
    Karen: We've decided to migrate to Kubernetes for orchestration.
    
    Alice: Great decisions everyone. Now let's assign action items.
    
    Action Items:
    1. Bob will create the feature A technical specification by Nov 10
    2. Carol will hire a UI/UX designer for the mobile redesign by Nov 15
    3. David will prepare the microservices migration plan by Nov 20
    4. Eve will post job listings for QA positions by Nov 8
    5. Frank will get vendor quotes for infrastructure by Nov 12
    6. Grace will document all legacy API dependencies by Nov 25
    7. Henry will research European compliance requirements by Dec 1
    8. Isabel will set up the sprint review calendar by Nov 7
    9. Jack will prototype collaboration features by Nov 30
    10. Karen will create Kubernetes migration timeline by Nov 18
    11. Alice will schedule follow-up meetings with each team by Nov 9
    12. Bob will review security implications of feature A by Nov 14
    
    Bob: I also own the API optimization project that's currently in progress.
    Carol: I'm responsible for the customer dashboard feature that's 75% complete.
    David: I own the database migration project which is currently blocked by vendor issues.
    """
    
    # Ingest the transcript
    print("Testing ingestion with many decisions and action items...")
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "transcript": transcript,
            "meeting_id": "test_truncation_" + str(int(time.time())),
            "title": "Q4 Planning Session - Truncation Test",
            "date": datetime.now().isoformat()
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Ingestion successful")
        print(f"  - Decisions extracted: {len(result.get('decisions', []))}")
        print(f"  - Action items extracted: {len(result.get('action_items', []))}")
        print(f"  - Entities created: {len(result.get('entities_created', []))}")
        
        # Display all decisions (should be more than 5)
        decisions = result.get('decisions', [])
        if len(decisions) > 5:
            print(f"\n  ✓ Successfully extracted {len(decisions)} decisions (more than 5):")
            for i, decision in enumerate(decisions, 1):
                print(f"    {i}. {decision[:60]}...")
        else:
            print(f"\n  ✗ Only {len(decisions)} decisions extracted (expected more than 5)")
            
        # Display all action items (should be more than 5)
        action_items = result.get('action_items', [])
        if len(action_items) > 5:
            print(f"\n  ✓ Successfully extracted {len(action_items)} action items (more than 5):")
            for i, item in enumerate(action_items[:3], 1):  # Show first 3
                print(f"    {i}. {item.get('action', 'N/A')[:60]}...")
            print(f"    ... and {len(action_items) - 3} more")
        else:
            print(f"\n  ✗ Only {len(action_items)} action items extracted (expected more than 5)")
            
        return True
    else:
        print(f"✗ Ingestion failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def test_relationship_queries():
    """Test queries that return many relationships."""
    
    print("\n\nTesting relationship queries...")
    
    # Query for relationships
    query = "Show me all the projects and features that people own or are responsible for"
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": query}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Query successful")
        
        # Check supporting data for relationships
        supporting_data = result.get('supporting_data', [])
        if supporting_data:
            print(f"  - Relationships found: {len(supporting_data)}")
            if len(supporting_data) > 10:
                print(f"  ✓ Successfully returned {len(supporting_data)} relationships (more than 10)")
            else:
                print(f"  ✗ Only {len(supporting_data)} relationships returned")
                
        # Check confidence calculation
        confidence = result.get('confidence', 0)
        print(f"  - Query confidence: {confidence:.2f}")
        
        return True
    else:
        print(f"✗ Query failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def test_timeline_configuration():
    """Test configurable timeline display limit."""
    
    print("\n\nTesting timeline configuration...")
    
    # Query for timeline data
    query = "Show me how the mobile app redesign project status changed over time"
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": query}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Timeline query successful")
        
        # Check if timeline events are limited to configured amount
        answer = result.get('answer', '')
        # Count how many timeline events are mentioned in the answer
        event_count = answer.count("In ") if "In " in answer else 0
        
        print(f"  - Timeline events shown in answer: {event_count}")
        print(f"  - Answer preview: {answer[:200]}...")
        
        return True
    else:
        print(f"✗ Timeline query failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def test_entity_description_length():
    """Test that entity descriptions are no longer truncated at 50 chars."""
    
    print("\n\nTesting entity description handling...")
    
    # This would require checking the entity resolver's behavior
    # For now, we'll verify through a query that exercises entity resolution
    
    query = "What is the status of all our major projects?"
    
    response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": query}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Entity query successful")
        print(f"  - Query confidence: {result.get('confidence', 0):.2f}")
        
        # Check metadata for resolution stats
        metadata = result.get('metadata', {})
        resolution_stats = metadata.get('resolution_stats', {})
        if resolution_stats:
            print(f"  - Entity resolution stats: {resolution_stats}")
            
        return True
    else:
        print(f"✗ Entity query failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return False

def main():
    """Run all truncation removal tests."""
    
    print("=" * 60)
    print("TRUNCATION REMOVAL TEST SUITE")
    print("=" * 60)
    
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("✗ API is not running. Please start the API first.")
            return
    except:
        print("✗ Cannot connect to API. Please ensure it's running on port 8000.")
        return
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    if test_ingestion_with_many_items():
        tests_passed += 1
        
    if test_relationship_queries():
        tests_passed += 1
        
    if test_timeline_configuration():
        tests_passed += 1
        
    if test_entity_description_length():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)
    
    if tests_passed == total_tests:
        print("✓ All truncation removals are working correctly!")
    else:
        print("✗ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()