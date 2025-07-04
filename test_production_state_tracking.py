#!/usr/bin/env python3
"""
Test production-ready state tracking implementation.
This tests the complete flow from ingestion through state tracking to queries.
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Any

API_BASE = "http://localhost:8000"

def ingest_meeting(title: str, transcript: str) -> Dict[str, Any]:
    """Ingest a meeting and return the response."""
    response = requests.post(
        f"{API_BASE}/api/ingest",
        json={
            "title": title,
            "transcript": transcript,
            "date": datetime.now().isoformat()
        },
        timeout=120.0
    )
    response.raise_for_status()
    return response.json()

def query_bi(query: str) -> Dict[str, Any]:
    """Run a business intelligence query."""
    response = requests.post(
        f"{API_BASE}/api/query",
        json={"query": query},
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()

def get_entity_timeline(entity_id: str) -> List[Dict[str, Any]]:
    """Get timeline for an entity."""
    response = requests.get(
        f"{API_BASE}/api/entities/{entity_id}/timeline",
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()["timeline"]

def test_state_transitions():
    """Test that state transitions are properly tracked."""
    print("\n=== Testing State Transition Tracking ===\n")
    
    # Meeting 1: Initial project planning
    print("1. Ingesting initial project meeting...")
    meeting1 = ingest_meeting(
        "Project Alpha Kickoff",
        """
        Team meeting for Project Alpha kickoff.
        
        Sarah: I'll be leading Project Alpha. We're currently in the planning phase.
        
        John: Great! What's the timeline?
        
        Sarah: We're planning to start development next week. The API redesign is our first milestone.
        
        Mike: I'll handle the database migration once we finalize the schema.
        
        Sarah: Perfect. So to summarize:
        - Project Alpha is in planning phase
        - API redesign will start next week  
        - Database migration is pending schema finalization
        - I'm the project lead
        """
    )
    print(f"   ✓ Meeting ingested: {meeting1['id']}")
    print(f"   - Entities found: {meeting1['entity_count']}")
    print(f"   - Memories extracted: {meeting1['memory_count']}")
    
    # Small delay to ensure processing completes
    time.sleep(2)
    
    # Meeting 2: Progress update with state changes
    print("\n2. Ingesting progress update meeting...")
    meeting2 = ingest_meeting(
        "Project Alpha Week 1 Update",
        """
        Weekly sync for Project Alpha progress.
        
        Sarah: Quick update on Project Alpha - we're now actively working on it. 
        
        John: How's the API redesign going?
        
        Sarah: The API redesign is in progress. We've completed the design phase and Mike started coding yesterday. About 30% done.
        
        Mike: Yes, making good progress. However, the database migration is blocked. We need vendor approval for the new schema before I can proceed.
        
        Sarah: Right. I'll follow up with the vendor. Also, good news - our initial requirements gathering is complete.
        
        Summary of changes:
        - Project Alpha: planning → in_progress
        - API redesign: planned → in_progress (30% complete)
        - Database migration: pending → blocked (waiting on vendor)
        - Requirements gathering: in_progress → completed
        """
    )
    print(f"   ✓ Meeting ingested: {meeting2['id']}")
    print(f"   - Entities found: {meeting2['entity_count']}")
    
    time.sleep(2)
    
    # Meeting 3: More state changes
    print("\n3. Ingesting completion meeting...")
    meeting3 = ingest_meeting(
        "Project Alpha Sprint Review",
        """
        Sprint review meeting.
        
        Sarah: Great news everyone! The API redesign is now complete. Mike finished it yesterday.
        
        Mike: Thanks! The database migration is also unblocked now. The vendor approved our schema and I'm actively working on the migration. Should be done by end of week.
        
        John: Excellent progress. What about testing?
        
        Sarah: Testing is now in progress. Jane started yesterday and found a few minor issues.
        
        Jane: Yes, nothing major. The test environment setup is complete though.
        
        Status updates:
        - API redesign: in_progress → completed
        - Database migration: blocked → in_progress  
        - Testing: planned → in_progress
        - Test environment setup: in_progress → completed
        """
    )
    print(f"   ✓ Meeting ingested: {meeting3['id']}")
    
    time.sleep(3)
    
    # Now test queries to verify state tracking
    print("\n=== Verifying State Tracking ===\n")
    
    # Test 1: Timeline query
    print("4. Testing timeline query for Project Alpha...")
    timeline_result = query_bi("Show me the timeline for Project Alpha")
    print(f"   ✓ Timeline query completed")
    print(f"   - Answer: {timeline_result['answer'][:200]}...")
    print(f"   - Confidence: {timeline_result['confidence']}")
    
    # Test 2: Current status query
    print("\n5. Testing current status query...")
    status_result = query_bi("What's the current status of all projects?")
    print(f"   ✓ Status query completed")
    print(f"   - Intent type: {status_result['intent']['type']}")
    print(f"   - Entities found: {len(status_result['entities_involved'])}")
    
    # Test 3: Blocker query
    print("\n6. Testing blocker detection...")
    blocker_result = query_bi("What tasks are currently blocked?")
    print(f"   ✓ Blocker query completed")
    print(f"   - Answer: {blocker_result['answer'][:200]}...")
    
    # Test 4: Progress tracking
    print("\n7. Testing progress tracking...")
    progress_result = query_bi("What's the progress on the API redesign?")
    print(f"   ✓ Progress query completed")
    print(f"   - Answer: {progress_result['answer']}")
    
    # Test 5: Assignment tracking
    print("\n8. Testing assignment tracking...")
    assignment_result = query_bi("What is Mike working on?")
    print(f"   ✓ Assignment query completed")
    print(f"   - Answer: {assignment_result['answer'][:200]}...")
    
    # Verify transition counts
    print("\n=== Validation Summary ===\n")
    
    # Get entity list to check transitions
    entities_response = requests.get(f"{API_BASE}/api/entities")
    entities = entities_response.json()
    
    print(f"Total entities tracked: {len(entities)}")
    
    # Check key entities
    key_entities = ["Project Alpha", "API redesign", "database migration"]
    for entity_name in key_entities:
        entity = next((e for e in entities if entity_name.lower() in e['name'].lower()), None)
        if entity:
            timeline = get_entity_timeline(entity['id'])
            print(f"\n{entity['name']}:")
            print(f"  - Current state: {entity.get('current_state', {})}")
            print(f"  - State changes: {len(timeline)}")
            
            # Show transitions
            for i, change in enumerate(timeline[:3]):  # Show first 3
                print(f"  - Change {i+1}: {change.get('from_state', {}).get('status', 'unknown')} → {change.get('to_state', {}).get('status', 'unknown')}")

def test_implicit_state_detection():
    """Test pattern-based implicit state detection."""
    print("\n\n=== Testing Implicit State Detection ===\n")
    
    meeting = ingest_meeting(
        "Quick Status Update",
        """
        Brief status update on various initiatives.
        
        Tom: Just a quick update - I'm now working on the security audit. Started this morning.
        
        Lisa: Great! The infrastructure upgrade is complete. We finished it last night.
        
        Tom: Oh, and the compliance review is blocked. We're waiting on legal approval.
        
        Lisa: The monitoring setup is making good progress. About 60% done.
        
        Tom: One more thing - we successfully delivered the Q3 report yesterday. It's all wrapped up.
        """
    )
    
    print(f"✓ Meeting ingested: {meeting['id']}")
    time.sleep(2)
    
    # Query for inferred states
    print("\nVerifying implicit state detection:")
    
    # Check security audit (should be in_progress)
    result1 = query_bi("What's the status of the security audit?")
    print(f"\n1. Security audit status: {result1['answer']}")
    
    # Check infrastructure upgrade (should be completed)
    result2 = query_bi("Is the infrastructure upgrade complete?")
    print(f"\n2. Infrastructure upgrade: {result2['answer']}")
    
    # Check compliance review (should be blocked)
    result3 = query_bi("What's blocking the compliance review?")
    print(f"\n3. Compliance review: {result3['answer']}")
    
    # Check monitoring setup (should show progress)
    result4 = query_bi("What's the progress on monitoring setup?")
    print(f"\n4. Monitoring setup: {result4['answer']}")

def test_complex_queries():
    """Test complex business intelligence queries."""
    print("\n\n=== Testing Complex Query Processing ===\n")
    
    # Test ownership query
    print("1. Testing ownership tracking...")
    ownership = query_bi("Who owns Project Alpha and what's their current focus?")
    print(f"   Answer: {ownership['answer']}")
    
    # Test multi-entity query
    print("\n2. Testing multi-entity status...")
    multi = query_bi("Show me all in-progress items and who's working on them")
    print(f"   Answer: {multi['answer'][:300]}...")
    
    # Test analytics query
    print("\n3. Testing analytics...")
    analytics = query_bi("How many tasks moved from blocked to in-progress this week?")
    print(f"   Answer: {analytics['answer']}")
    
    # Test dependency query
    print("\n4. Testing dependency tracking...")
    deps = query_bi("What items depend on vendor approval?")
    print(f"   Answer: {deps['answer']}")

def main():
    """Run all production state tracking tests."""
    print("="*60)
    print("PRODUCTION STATE TRACKING TEST SUITE")
    print("="*60)
    
    try:
        # Verify API is running
        health = requests.get(f"{API_BASE}/").json()
        print(f"\n✓ API is healthy: {health['service']} v{health['version']}")
        
        # Run test suites
        test_state_transitions()
        test_implicit_state_detection()
        test_complex_queries()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())