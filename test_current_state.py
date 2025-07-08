#!/usr/bin/env python3
"""Test current state of the API after Phase 1 & 2 fixes."""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_current_state():
    print("=== COMPREHENSIVE API STATE TEST ===\n")
    
    # Test 1: Basic health check
    print("1. Health Check")
    print("-" * 40)
    response = requests.get(f"{BASE_URL}/health/detailed")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        health = response.json()
        print(f"Database: {health['database']['status']}")
        print(f"Vector DB: {health['vector_db']['status']}")
        print(f"Entities: {health['database']['entities']}")
        print(f"Memories: {health['vector_db']['collection_info']['memories']['vectors_count']}")
    
    # Test 2: Test string formatting fix (Phase 1)
    print("\n\n2. Phase 1 Test: String Formatting with %")
    print("-" * 40)
    test_data = {
        "transcript": "Alice: The 50% Milestone Project is at 75% completion.",
        "meeting_date": datetime.now().isoformat(),
        "title": "Test % Characters"
    }
    response = requests.post(f"{BASE_URL}/api/ingest", json=test_data)
    print(f"Ingest Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text[:200]}")
    
    # Test 3: Query with % character
    print("\n\n3. Query with % Character")
    print("-" * 40)
    response = requests.post(f"{BASE_URL}/api/query", 
                           json={"query": "What is the status of the 50% Milestone Project?"})
    print(f"Query Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Answer preview: {result['answer'][:150]}...")
    else:
        print(f"Error: {response.text[:200]}")
    
    # Test 4: State normalization (Phase 2)
    print("\n\n4. Phase 2 Test: State Normalization")
    print("-" * 40)
    test_data = {
        "transcript": """
        Bob: Project A is In Progress.
        Carol: Project B is in_progress.
        Dave: Project C is IN-PROGRESS.
        """,
        "meeting_date": datetime.now().isoformat(),
        "title": "State Format Test"
    }
    response = requests.post(f"{BASE_URL}/api/ingest", json=test_data)
    print(f"Ingest Status: {response.status_code}")
    
    # Query to check normalization
    response = requests.post(f"{BASE_URL}/api/query", 
                           json={"query": "How many projects are in progress?"})
    print(f"Query Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Answer: {result['answer'][:200]}...")
    
    # Test 5: Entity extraction issues
    print("\n\n5. Entity Extraction Issues")
    print("-" * 40)
    response = requests.post(f"{BASE_URL}/api/query", 
                           json={"query": "What projects exist?"})
    if response.status_code == 200:
        result = response.json()
        entities = result.get('entities_involved', [])
        print(f"Entities found: {len(entities)}")
        for e in entities[:5]:
            print(f"  - {e['name']} ({e['type']})")
    
    # Test 6: Check for warnings in logs
    print("\n\n6. Current Issues from Recent Activity")
    print("-" * 40)
    # Get entity list
    response = requests.get(f"{BASE_URL}/api/entities")
    if response.status_code == 200:
        entities = response.json()
        print(f"Total entities: {len(entities)}")
        
        # Check for problematic entities
        problematic = [e for e in entities if e['name'] in ['What', 'December', 'Status']]
        if problematic:
            print("Problematic entities found:")
            for e in problematic:
                print(f"  - {e['name']} (ID: {e['id']})")

if __name__ == "__main__":
    test_current_state()