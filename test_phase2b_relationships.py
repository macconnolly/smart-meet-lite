#!/usr/bin/env python3
"""Test Phase 2b: Relationship type normalization."""

import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api import app
from fastapi.testclient import TestClient


def test_relationship_normalization():
    """Test that relationship type variations are normalized correctly."""
    client = TestClient(app)
    
    print("Testing Phase 2b: Relationship Normalization\n")
    
    # Test transcript with various relationship type variations
    test_transcript = """
    Meeting about project assignments:
    
    Sarah: Let me clarify the current assignments.
    
    Bob is responsible for Project Alpha - he owns the delivery timeline.
    
    Alice works on the Mobile App Redesign and is also responsible for the UX components.
    
    Charlie is working on API Migration which depends on the Authentication Module.
    
    Dave: The Payment Integration project blocks the Launch milestone.
    
    Sarah: Also, the Mobile App needs the API Migration to be completed first.
    
    Bob reports to Sarah for all project decisions.
    
    Alice collaborates with Charlie on the shared components.
    """
    
    print("1. Testing ingestion with relationship variations...")
    
    # Clear any existing logs first
    log_file = "api_debug.log"
    if os.path.exists(log_file):
        # Read current size to know where to start checking
        initial_size = os.path.getsize(log_file)
    else:
        initial_size = 0
    
    # Ingest the meeting
    ingest_response = client.post("/api/ingest", json={
        "title": "Project Assignment Meeting",
        "transcript": test_transcript,
        "date": datetime.now().isoformat()
    })
    
    if ingest_response.status_code == 200:
        print("  ✓ Ingestion successful")
        result = ingest_response.json()
        
        # Check for relationships in the response
        if 'relationships_created' in result:
            print(f"  ✓ Created {result['relationships_created']} relationships")
        
        # Check the logs for warnings
        print("\n2. Checking for relationship warnings in logs...")
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                f.seek(initial_size)  # Start from where we were
                new_logs = f.read()
                
                # Count relationship warnings
                relationship_warnings = []
                for line in new_logs.split('\n'):
                    if 'Invalid relationship type' in line:
                        relationship_warnings.append(line)
                
                if relationship_warnings:
                    print(f"  ✗ Found {len(relationship_warnings)} relationship warnings:")
                    for warning in relationship_warnings[:5]:  # Show first 5
                        print(f"    - {warning}")
                else:
                    print("  ✓ No relationship warnings found")
        
        # Test a query to verify relationships work
        print("\n3. Testing query with relationships...")
        query_response = client.post("/api/query", json={
            "query": "Who is responsible for Project Alpha?"
        })
        
        if query_response.status_code == 200:
            print("  ✓ Query successful")
            answer = query_response.json().get('answer', '')
            if 'Bob' in answer:
                print("  ✓ Correctly identified Bob as responsible")
            else:
                print("  ✗ Failed to identify responsibility")
                print(f"    Answer: {answer}")
        else:
            print(f"  ✗ Query failed with status {query_response.status_code}")
        
        # Test dependency query
        print("\n4. Testing dependency relationships...")
        dep_response = client.post("/api/query", json={
            "query": "What does the API Migration depend on?"
        })
        
        if dep_response.status_code == 200:
            print("  ✓ Dependency query successful")
            answer = dep_response.json().get('answer', '')
            if 'Authentication' in answer:
                print("  ✓ Correctly identified dependency")
            else:
                print("  ? Dependency not clearly identified")
                print(f"    Answer: {answer}")
        else:
            print(f"  ✗ Dependency query failed")
            
    else:
        print(f"  ✗ Ingestion failed with status {ingest_response.status_code}")
        print(f"  Error: {ingest_response.text}")
        return False
    
    print("\n✓ Phase 2b testing complete!")
    return True


if __name__ == "__main__":
    success = test_relationship_normalization()
    sys.exit(0 if success else 1)