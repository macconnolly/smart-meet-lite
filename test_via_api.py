#!/usr/bin/env python3
"""
Test the batch processing via API calls.
This script sends test data to the API to verify state tracking improvements.
"""

import requests
import json
from datetime import datetime
import time

# Try multiple endpoints
API_BASES = ["http://127.0.0.1:8000", "http://localhost:8000", "http://0.0.0.0:8000"]
API_BASE = None

def test_state_tracking():
    """Test that state transitions are properly tracked."""
    print("=== Testing State Tracking via API ===\n")
    
    # Meeting 1: Initial states
    meeting1 = {
        "title": "Project Planning Meeting",
        "transcript": """
        Team meeting to discuss project status.
        
        Alice: Let's review our projects. Project Alpha is now in progress. 
        We've made good progress and are about 30% complete.
        
        Bob: Great! I'll be taking ownership of Project Alpha moving forward.
        
        Alice: Also, the API Migration feature is currently blocked. 
        We're waiting for the vendor to provide API credentials.
        
        Charlie: I'm working on the Database Upgrade project. It's still in planning phase.
        We expect to start actual work next sprint.
        """
    }
    
    print("Ingesting Meeting 1...")
    response = requests.post(f"{API_BASE}/api/ingest", json=meeting1)
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Meeting 1 ingested successfully")
        print(f"  - Entities: {result['entity_count']}")
        print(f"  - Memories: {result['memory_count']}")
        print(f"  - State Changes: {result.get('state_change_count', 'N/A')}")
    else:
        print(f"✗ Error: {response.status_code} - {response.text}")
        return
    
    # Meeting 2: State changes
    meeting2 = {
        "title": "Progress Update Meeting",
        "transcript": """
        Weekly progress update meeting.
        
        Bob: Quick update on Project Alpha - we're now at 50% completion.
        The team has been making steady progress.
        
        Alice: Excellent! What about the API Migration?
        
        Charlie: Good news - the API Migration is no longer blocked! 
        We received the vendor credentials yesterday. It's now in progress.
        
        Bob: The Database Upgrade has also moved from planning to in progress.
        We started the initial schema design work.
        
        Alice: One concern - Project Beta is now blocked due to resource constraints.
        We need to hire additional developers before we can proceed.
        """
    }
    
    print("\nIngesting Meeting 2...")
    response = requests.post(f"{API_BASE}/api/ingest", json=meeting2)
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Meeting 2 ingested successfully")
        print(f"  - Entities: {result['entity_count']}")
        print(f"  - Memories: {result['memory_count']}")
        print(f"  - State Changes: {result.get('state_change_count', 'N/A')}")
    else:
        print(f"✗ Error: {response.status_code} - {response.text}")
        return
    
    # Query for state changes
    print("\n=== Querying State Changes ===")
    
    queries = [
        "What is the current status of Project Alpha?",
        "Show me the timeline of changes for API Migration",
        "Which projects are currently blocked?",
        "What progress has been made on all projects?"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        try:
            response = requests.post(f"{API_BASE}/api/query", json={"query": query})
            
            # Log the raw response for debugging
            print(f"Response status: {response.status_code}")
            if response.status_code != 200:
                print(f"Response text: {response.text[:500]}...")  # First 500 chars
            
            if response.status_code == 200:
                result = response.json()
                print(f"Answer: {result['answer']}")
                if 'confidence' in result:
                    print(f"Confidence: {result['confidence']:.2f}")
            else:
                print(f"✗ Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"✗ Exception: {e}")

def check_api_health():
    """Check if API is running and ready."""
    global API_BASE
    
    for base in API_BASES:
        try:
            response = requests.get(f"{base}/", timeout=2)
            if response.status_code == 200:
                API_BASE = base
                print(f"✓ API is running and ready at {base}\n")
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
    
    print("✗ API is not running on any expected endpoint")
    print("Please start the API with: make run")
    return False

if __name__ == "__main__":
    if check_api_health():
        test_state_tracking()
    else:
        print("\nPlease start the API first!")