#!/usr/bin/env python3
"""Test Phase 2: State Normalization using the API."""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_phase2_state_normalization():
    """Test that state normalization prevents fake state changes."""
    print("\n=== Testing Phase 2: State Normalization via API ===\n")
    
    # First, ingest test data with various state formats
    print("Step 1: Ingesting test meeting with mixed state formats")
    print("-" * 50)
    
    test_transcript = """
    Meeting: State Normalization Test
    Date: 2025-01-07
    Participants: Alice, Bob, Carol
    
    Alice: Let's check on our projects.
    
    Bob: Project Alpha is currently In Progress.
    
    Alice: Good. What about Project Beta?
    
    Bob: Project Beta is in_progress as well.
    
    Carol: Mobile App is in-progress too.
    
    Alice: And the API Migration?
    
    Bob: API Migration is IN PROGRESS.
    
    Alice: Great, so all four projects are actively being worked on.
    """
    
    ingest_payload = {
        "transcript": test_transcript,
        "meeting_date": datetime.now().isoformat(),
        "title": "State Normalization Test Meeting"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ingest", json=ingest_payload)
        if response.status_code == 200:
            print("✅ Meeting ingested successfully")
            ingest_result = response.json()
            print(f"   Extracted {len(ingest_result.get('entities', []))} entities")
        else:
            print(f"❌ Failed to ingest meeting: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error ingesting meeting: {e}")
        return False
    
    # Wait a moment for processing
    import time
    time.sleep(1)
    
    # Now ingest a second meeting with the same states but different formatting
    print("\n\nStep 2: Ingesting follow-up meeting with same states, different formatting")
    print("-" * 50)
    
    test_transcript2 = """
    Meeting: Follow-up Meeting
    Date: 2025-01-07
    Participants: Alice, Bob
    
    Alice: Quick status check on our projects.
    
    Bob: Project Alpha is still in progress. No change.
    
    Alice: And Project Beta?
    
    Bob: Project Beta remains In_Progress.
    
    Alice: Mobile App?
    
    Bob: Mobile App is still IN-PROGRESS.
    
    Alice: API Migration?
    
    Bob: API Migration continues to be in progress.
    """
    
    ingest_payload2 = {
        "transcript": test_transcript2,
        "meeting_date": datetime.now().isoformat(),
        "title": "Follow-up State Check"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ingest", json=ingest_payload2)
        if response.status_code == 200:
            print("✅ Follow-up meeting ingested successfully")
        else:
            print(f"❌ Failed to ingest follow-up: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Test various queries to check normalization
    print("\n\nStep 3: Testing queries for state normalization")
    print("=" * 70)
    
    test_queries = [
        {
            "name": "Timeline query",
            "query": "Show me the timeline for Project Alpha",
            "check_for": ["capitalization", "formatting", "no change", "no state change"]
        },
        {
            "name": "Status query",
            "query": "What is the current status of all projects?",
            "check_for": ["in_progress", "In Progress", "consistent"]
        },
        {
            "name": "State transition query", 
            "query": "Have there been any state changes in Project Beta?",
            "check_for": ["no changes", "same state", "no transitions"]
        }
    ]
    
    all_passed = True
    
    for test in test_queries:
        print(f"\nTest: {test['name']}")
        print(f"Query: {test['query']}")
        print("-" * 50)
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/query",
                json={"query": test['query']},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '').lower()
                
                # Check that response doesn't mention capitalization/formatting changes
                bad_phrases = [
                    'capitalization',
                    'formatting change',
                    'format change',
                    'in progress to in_progress',
                    'in_progress to in progress'
                ]
                
                found_bad_phrases = [phrase for phrase in bad_phrases if phrase in answer]
                
                if not found_bad_phrases:
                    print("✅ No false state changes detected")
                else:
                    print("❌ Found references to formatting changes:", found_bad_phrases)
                    all_passed = False
                
                # Check for expected content
                found_expected = False
                for expected in test['check_for']:
                    if expected.lower() in answer:
                        found_expected = True
                        break
                
                print(f"   Answer preview: {result.get('answer', '')[:150]}...")
                
            else:
                print(f"❌ Query failed with status {response.status_code}")
                print(f"   Error: {response.text[:200]}")
                all_passed = False
                
        except Exception as e:
            print(f"❌ Error making query: {e}")
            all_passed = False
    
    # Test normalized state values
    print("\n\nStep 4: Testing canonical state values")
    print("=" * 70)
    
    state_test_transcript = """
    Meeting: State Value Test
    Date: 2025-01-07
    
    Alice: Let's test various state values.
    
    Bob: Project Gamma is COMPLETED.
    Carol: Project Delta is complete.
    Dave: Project Epsilon is Done.
    Eve: Project Zeta is finished.
    
    Alice: And the blocked ones?
    
    Bob: Project Eta is BLOCKED.
    Carol: Project Theta is on hold.
    Dave: Project Iota is on_hold.
    """
    
    # Ingest this test data
    response = requests.post(f"{BASE_URL}/api/ingest", json={
        "transcript": state_test_transcript,
        "meeting_date": datetime.now().isoformat(),
        "title": "State Value Test"
    })
    
    if response.status_code == 200:
        print("✅ State value test data ingested")
        
        # Query to check normalization
        response = requests.post(f"{BASE_URL}/api/query", json={
            "query": "How many projects are completed? How many are blocked?"
        })
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            print(f"   Answer: {answer[:200]}...")
            
            # Should show all as same state despite different inputs
            if "4" in answer or "four" in answer.lower():
                print("✅ Completed states normalized correctly")
            else:
                print("❌ Completed states not properly normalized")
                all_passed = False
                
            if "3" in answer or "three" in answer.lower():
                print("✅ Blocked states normalized correctly")
            else:
                print("❌ Blocked states not properly normalized")
                all_passed = False
    
    print("\n\n=== Phase 2 API Testing Complete ===")
    if all_passed:
        print("✅ All tests passed! State normalization is working correctly.")
    else:
        print("❌ Some tests failed. State normalization may need adjustment.")
    
    return all_passed

if __name__ == "__main__":
    success = test_phase2_state_normalization()
    sys.exit(0 if success else 1)