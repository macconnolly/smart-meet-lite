#!/usr/bin/env python3
"""Test query parsing to see LLM responses."""

import requests
import json

# Test queries
test_queries = [
    "What is the status of mobile app redesign?",
    "Who owns the API optimization project?",
    "Show me the timeline for navigation implementation",
    "How many projects are in progress?",
    "Find discussions about dark mode"
]

print("Testing Query Parsing with Enhanced Logging")
print("=" * 50)

for i, query in enumerate(test_queries, 1):
    print(f"\nTest {i}: {query}")
    print("-" * 30)
    
    response = requests.post(
        "http://localhost:8000/api/query",
        json={"query": query}
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Intent: {result.get('intent', {}).get('type', 'N/A')}")
        print(f"Answer: {result.get('answer', 'N/A')[:100]}...")
        print(f"Confidence: {result.get('confidence', 'N/A')}")
        print(f"Entities found: {len(result.get('entities_involved', []))}")
        supporting_data = result.get('supporting_data', [])
        if supporting_data:
            print(f"Supporting data items: {len(supporting_data)}")
    else:
        print(f"Error: {response.text}")

print("\n" + "=" * 50)
print("Check the API logs to see the raw LLM responses!")