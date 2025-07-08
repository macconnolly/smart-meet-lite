#!/usr/bin/env python3
"""Test Phase 1: String Formatting Fix using the API."""

import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_phase1_via_api():
    """Test that the API handles queries with % characters correctly."""
    print("\n=== Testing Phase 1: String Formatting Fix via API ===\n")
    
    # First, let's ingest some test data with % characters
    print("Step 1: Ingesting test meeting with % characters in entity data")
    print("-" * 50)
    
    test_transcript = """
    Meeting: Q4 Planning Session
    Date: 2025-01-07
    Participants: Alice, Bob, Carol
    
    Alice: Let's discuss the 50% Milestone Project. We need to hit our targets.
    
    Bob: The 50% Milestone Project is currently at 25% completion. We're making good progress.
    
    Carol: I'm concerned about performance. Our CPU usage is hitting 90% during peak loads.
    
    Alice: That's a blocker. We need to optimize before we can proceed.
    
    Bob: I'll take ownership of the performance optimization. We should target 75% CPU usage maximum.
    
    Carol: Also, our Q4 Sales Target is at 75% achievement. We're at $750K of our $1M goal.
    
    Alice: Good progress on sales. Let's ensure the 50% Milestone Project doesn't slip.
    """
    
    ingest_payload = {
        "transcript": test_transcript,
        "meeting_date": datetime.now().isoformat(),
        "title": "Q4 Planning with Percentage Metrics"
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
    
    # Now test various queries that would have failed before the fix
    test_queries = [
        {
            "name": "Status query with % in entity name",
            "query": "What is the status of the 50% Milestone Project?",
            "expected_keywords": ["50%", "milestone", "25%", "completion"]
        },
        {
            "name": "Blocker query with % in description",
            "query": "What are the current blockers?",
            "expected_keywords": ["CPU", "90%", "performance"]
        },
        {
            "name": "Analytics query with % metrics",
            "query": "What are the metrics for Q4?",
            "expected_keywords": ["75%", "sales", "$750K"]
        },
        {
            "name": "Timeline query with % progress",
            "query": "Show me the timeline for the 50% Milestone Project",
            "expected_keywords": ["25%", "progress"]
        },
        {
            "name": "Ownership query with % targets",
            "query": "Who owns the performance optimization?",
            "expected_keywords": ["Bob", "75%", "CPU"]
        }
    ]
    
    print("\n\nStep 2: Testing queries with % characters")
    print("=" * 70)
    
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
                answer = result.get('answer', '')
                
                # Check if the response contains expected content
                found_keywords = []
                missing_keywords = []
                
                for keyword in test['expected_keywords']:
                    if keyword.lower() in answer.lower():
                        found_keywords.append(keyword)
                    else:
                        missing_keywords.append(keyword)
                
                if not missing_keywords:
                    print("✅ Query succeeded! Response contains all expected keywords")
                else:
                    print("⚠️  Query succeeded but missing keywords:", missing_keywords)
                
                print(f"   Answer preview: {answer[:150]}...")
                print(f"   Confidence: {result.get('confidence', 0)}")
                print(f"   Intent: {result.get('intent', {}).get('intent_type', 'unknown')}")
                
            else:
                print(f"❌ Query failed with status {response.status_code}")
                print(f"   Error: {response.text[:200]}")
                all_passed = False
                
                # Check if it's the specific % formatting error
                if "Invalid format specifier" in response.text:
                    print("   ⚠️  This is the exact error Phase 1 should fix!")
                
        except Exception as e:
            print(f"❌ Error making query: {e}")
            all_passed = False
    
    # Test edge cases
    print("\n\nStep 3: Testing edge cases")
    print("=" * 70)
    
    edge_cases = [
        {
            "name": "Multiple % signs",
            "query": "What's the status of items between 0% and 100%?"
        },
        {
            "name": "% at end of query",
            "query": "Show me all projects at 50%"
        },
        {
            "name": "Complex % formatting",
            "query": "Compare 25% progress vs 75% target"
        }
    ]
    
    for test in edge_cases:
        print(f"\nEdge case: {test['name']}")
        print(f"Query: {test['query']}")
        print("-" * 30)
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/query",
                json={"query": test['query']},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print("✅ Query succeeded without formatting errors")
            else:
                print(f"❌ Query failed with status {response.status_code}")
                if "Invalid format specifier" in response.text:
                    print("   ⚠️  String formatting error still present!")
                    all_passed = False
                
        except Exception as e:
            print(f"❌ Error: {e}")
            all_passed = False
    
    print("\n\n=== Phase 1 API Testing Complete ===")
    if all_passed:
        print("✅ All tests passed! String formatting fix is working correctly.")
    else:
        print("❌ Some tests failed. The fix may not be complete.")
    
    return all_passed

if __name__ == "__main__":
    success = test_phase1_via_api()
    sys.exit(0 if success else 1)