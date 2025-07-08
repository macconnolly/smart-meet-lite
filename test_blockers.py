#!/usr/bin/env python3
"""Debug blocker query issue."""

import requests
import json

API_BASE = "http://127.0.0.1:8000"

# Test data with explicit blockers
meeting1 = {
    "title": "Blocker Test Meeting",
    "transcript": """
    Alice: Project Beta is now blocked. We're waiting for vendor approval.
    Bob: Also, the Database Migration is blocked due to missing credentials.
    Charlie: I'll add those to our blocker list.
    """
}

print("1. Ingesting meeting with blockers...")
response = requests.post(f"{API_BASE}/api/ingest", json=meeting1)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"   Entities: {result['entity_count']}")

print("\n2. Querying for blockers...")
query = {"query": "Which projects are currently blocked?"}
response = requests.post(f"{API_BASE}/api/query", json=query)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"   Answer: {result['answer'][:200]}...")
else:
    print(f"   Error: {response.text}")