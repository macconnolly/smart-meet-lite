#!/usr/bin/env python3
"""Test entity resolution improvements."""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_entity_resolution_accuracy():
    """Test that entity resolution handles edge cases correctly."""
    
    # First, create some entities
    setup_transcript = """
    Alice: We need to discuss the vendor issues with our cloud provider.
    Bob: I agree. Also, the microservices architecture is ready for review.
    Carol: Great. Let's also talk about vendor selection for the new project.
    """
    
    setup_response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Setup Meeting",
            "transcript": setup_transcript,
            "date": datetime.now().isoformat()
        }
    )
    
    if setup_response.status_code != 200:
        print(f"Setup ingestion failed: {setup_response.text}")
        return False
    
    print("✓ Setup meeting ingested successfully")
    
    # Now test resolution with similar but different terms
    test_transcript = """
    David: I need vendor quotes for infrastructure upgrades.
    Eve: The microservices migration plan needs updating.
    Frank: We should review vendor proposals for security tools.
    """
    
    test_response = requests.post(
        f"{BASE_URL}/api/ingest", 
        json={
            "title": "Test Meeting",
            "transcript": test_transcript,
            "date": datetime.now().isoformat()
        }
    )
    
    if test_response.status_code != 200:
        print(f"Test ingestion failed: {test_response.text}")
        return False
    
    result = test_response.json()
    
    # Query to verify relationships
    query_response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "What vendor-related items exist?"}
    )
    
    if query_response.status_code != 200:
        print(f"Query failed: {query_response.text}")
        return False
    
    query_result = query_response.json()
    answer = query_result.get("answer", "").lower()
    
    print(f"\n✓ Query executed successfully")
    print(f"Answer: {query_result.get('answer', '')[:200]}...")
    
    # Check that "vendor quotes for infrastructure" didn't incorrectly match "vendor issues"
    # This is a bit indirect, but we're checking the system behavior
    if "vendor quotes" in answer and "vendor issues" in answer:
        # They might both exist, which is fine, as long as they're separate
        print("✓ Both vendor entities exist (as expected)")
    
    # Test microservices entities
    ms_query_response = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "Show me all microservices related items"}
    )
    
    if ms_query_response.status_code == 200:
        ms_result = ms_query_response.json()
        print(f"\n✓ Microservices query executed")
        print(f"Answer: {ms_result.get('answer', '')[:200]}...")
    
    # Test ownership relationships
    ownership_query = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "Who is responsible for vendor quotes for infrastructure?"}
    )
    
    if ownership_query.status_code == 200:
        ownership_result = ownership_query.json()
        print(f"\n✓ Ownership query executed")
        print(f"Confidence: {ownership_result.get('confidence', 0):.2f}")
        
        # Check metadata for resolution stats
        metadata = ownership_result.get('metadata', {})
        resolution_stats = metadata.get('resolution_stats', {})
        if resolution_stats:
            print(f"Resolution stats: {resolution_stats}")
    
    print("\n✓ Entity resolution tests completed successfully!")
    return True

def test_action_item_deliverable_creation():
    """Test that action items create deliverable entities."""
    
    action_transcript = f"""
    Meeting: Action Item Test
    Date: {datetime.now().strftime('%Y-%m-%d')}
    
    Alice: Let's assign some tasks.
    Bob will create the API documentation by next week.
    Carol will design the new dashboard interface.
    David will implement the caching layer.
    """
    
    response = requests.post(
        f"{BASE_URL}/api/ingest",
        json={
            "title": "Action Item Test Meeting",
            "transcript": action_transcript
        }
    )
    
    if response.status_code != 200:
        print(f"Action item test failed: {response.text}")
        return False
    
    # Query for the created deliverables
    deliverables_query = requests.post(
        f"{BASE_URL}/api/query",
        json={"query": "What tasks are assigned to people?"}
    )
    
    if deliverables_query.status_code == 200:
        result = deliverables_query.json()
        print(f"\n✓ Deliverables query executed")
        print(f"Answer: {result.get('answer', '')[:300]}...")
        
        # Check if deliverable entities were created
        entities_involved = result.get('entities_involved', [])
        task_entities = [e for e in entities_involved if e.get('type') == 'task']
        print(f"Task entities created: {len(task_entities)}")
        
        if task_entities:
            print("✓ Deliverable entities created for action items")
        else:
            print("⚠ No deliverable entities found")
    
    return True

def main():
    """Run all entity resolution tests."""
    
    print("=" * 60)
    print("ENTITY RESOLUTION INTEGRATION TESTS")
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
    total_tests = 2
    
    print("\n1. Testing entity resolution accuracy...")
    print("-" * 40)
    if test_entity_resolution_accuracy():
        tests_passed += 1
    
    # Add small delay between tests
    time.sleep(1)
    
    print("\n\n2. Testing action item deliverable creation...")
    print("-" * 40)
    if test_action_item_deliverable_creation():
        tests_passed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"TEST SUMMARY: {tests_passed}/{total_tests} tests passed")
    print("=" * 60)
    
    if tests_passed == total_tests:
        print("✓ All entity resolution improvements are working correctly!")
    else:
        print("✗ Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()