#!/usr/bin/env python3
"""Quick test for state tracking functionality."""

import requests
import json
import time
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_state_tracking():
    """Test state tracking with two meetings."""
    
    # Meeting 1: Initial state
    print("1. Ingesting first meeting...")
    response1 = requests.post(
        f"{API_BASE}/api/ingest",
        json={
            "title": "Project Status Meeting 1",
            "transcript": """
            Sarah: I'm leading Project Alpha. It's currently in the planning phase.
            Mike: I'll handle the database migration once we start.
            Jane: The API redesign is planned for next sprint.
            """,
            "date": datetime.now().isoformat()
        },
        timeout=60.0
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"✓ Meeting 1 ingested: {data1['id']}")
        print(f"  Entities: {data1['entity_count']}, Memories: {data1['memory_count']}")
    else:
        print(f"✗ Failed: {response1.status_code} - {response1.text[:200]}")
        return
    
    # Wait a bit
    time.sleep(2)
    
    # Meeting 2: State changes
    print("\n2. Ingesting second meeting with state changes...")
    response2 = requests.post(
        f"{API_BASE}/api/ingest",
        json={
            "title": "Project Status Meeting 2",
            "transcript": """
            Sarah: Quick update - Project Alpha is now in progress. We started development yesterday.
            Mike: The database migration is blocked. We need vendor approval first.
            Jane: Good news - the API redesign is complete! Finished it this morning.
            Sarah: Also, Project Alpha is about 30% complete now.
            """,
            "date": datetime.now().isoformat()
        },
        timeout=60.0
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✓ Meeting 2 ingested: {data2['id']}")
        print(f"  Entities: {data2['entity_count']}, Memories: {data2['memory_count']}")
    else:
        print(f"✗ Failed: {response2.status_code} - {response2.text[:200]}")
        return
    
    # Query for state changes
    print("\n3. Querying for Project Alpha timeline...")
    response3 = requests.post(
        f"{API_BASE}/api/query",
        json={"query": "Show me the timeline for Project Alpha"},
        timeout=30.0
    )
    
    if response3.status_code == 200:
        result = response3.json()
        print(f"✓ Query successful")
        print(f"  Answer: {result['answer'][:300]}...")
    else:
        print(f"✗ Query failed: {response3.status_code}")
    
    # Check for transitions
    print("\n4. Checking state transitions...")
    
    # Get entities to check their timelines
    entities_response = requests.get(f"{API_BASE}/api/entities")
    if entities_response.status_code == 200:
        entities = entities_response.json()
        print(f"✓ Found {len(entities)} entities")
        
        # Check timeline for Project Alpha
        project_alpha = next((e for e in entities if "Project Alpha" in e['name']), None)
        if project_alpha:
            timeline_response = requests.get(f"{API_BASE}/api/entities/{project_alpha['id']}/timeline")
            if timeline_response.status_code == 200:
                timeline = timeline_response.json()['timeline']
                print(f"✓ Project Alpha has {len(timeline)} state changes")
                for i, change in enumerate(timeline[:3]):
                    print(f"  Change {i+1}: {change.get('reason', 'No reason')}")

if __name__ == "__main__":
    test_state_tracking()