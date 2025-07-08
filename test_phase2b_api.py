#!/usr/bin/env python3
"""Test Phase 2b: Relationship type normalization using the API."""

import requests
import json
import sys
import os
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

def test_phase2b_relationship_normalization():
    """Test that relationship type variations are normalized correctly."""
    print("\n=== Testing Phase 2b: Relationship Normalization via API ===\n")
    
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
    
    # Ingest the meeting
    ingest_payload = {
        "title": "Project Assignment Meeting",
        "transcript": test_transcript,
        "date": datetime.now().isoformat()
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/ingest", json=ingest_payload)
        if response.status_code == 200:
            print("✅ Ingestion successful")
            result = response.json()
            
            # Check for relationships in the response  
            if 'relationships' in result:
                print(f"   Created {len(result['relationships'])} relationships")
            if 'relationship_count' in result:
                print(f"   Relationship count: {result['relationship_count']}")
                
        else:
            print(f"❌ Ingestion failed with status {response.status_code}")
            print(f"   Error: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ Error ingesting meeting: {e}")
        return False
    
    # Give the system a moment to process
    time.sleep(1)
    
    # Test a query to verify relationships work
    print("\n2. Testing query with relationships...")
    
    query_tests = [
        {
            "query": "Who is responsible for Project Alpha?",
            "expected": ["Bob"],
            "description": "Responsibility relationship"
        },
        {
            "query": "What does the API Migration depend on?",
            "expected": ["Authentication"],
            "description": "Dependency relationship"
        },
        {
            "query": "Which projects does the Payment Integration block?",
            "expected": ["Launch"],
            "description": "Blocking relationship"
        },
        {
            "query": "Who reports to Sarah?",
            "expected": ["Bob"],
            "description": "Reporting relationship"
        }
    ]
    
    all_passed = True
    
    for test in query_tests:
        print(f"\nTest: {test['description']}")
        print(f"Query: {test['query']}")
        
        try:
            response = requests.post(f"{BASE_URL}/api/query", json={"query": test['query']})
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                
                # Check for expected entities in answer
                found = False
                for expected in test['expected']:
                    if expected.lower() in answer.lower():
                        found = True
                        print(f"✅ Found expected: {expected}")
                        break
                
                if not found:
                    print(f"❌ Expected entities not found")
                    print(f"   Answer: {answer[:150]}...")
                    all_passed = False
                    
            else:
                print(f"❌ Query failed with status {response.status_code}")
                print(f"   Error: {response.text[:200]}...")
                all_passed = False
                
        except Exception as e:
            print(f"❌ Error making query: {e}")
            all_passed = False
    
    # Check the logs for relationship warnings
    print("\n3. Checking for relationship warnings in logs...")
    
    log_file = "api_debug.log"
    if os.path.exists(log_file):
        # Look at the last 100 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            relationship_warnings = []
            for line in recent_lines:
                if 'Invalid relationship type' in line and 'test_phase2b' not in line:
                    # Extract the timestamp to see if it's recent
                    if '2025-' in line:  # Recent log entry
                        relationship_warnings.append(line.strip())
            
            if relationship_warnings:
                print(f"⚠️  Found {len(relationship_warnings)} relationship warnings")
                for warning in relationship_warnings[:3]:  # Show first 3
                    print(f"   - {warning}")
                # This is just a warning, not a failure
            else:
                print("✅ No relationship warnings found in recent logs")
    
    print("\n=== Phase 2b API Testing Complete ===")
    if all_passed:
        print("✅ All tests passed! Relationship normalization is working.")
    else:
        print("❌ Some tests failed. Check relationship handling.")
    
    return all_passed


if __name__ == "__main__":
    # Check if API is running
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code != 200:
            print("❌ API is not running. Please start it with: make run")
            sys.exit(1)
    except:
        print("❌ Cannot connect to API. Please start it with: make run")
        sys.exit(1)
        
    success = test_phase2b_relationship_normalization()
    sys.exit(0 if success else 1)