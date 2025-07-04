#!/usr/bin/env python3
"""Test simple query to debug the issue."""

import requests
import json

# Test entity retrieval first
print("Testing entity retrieval...")
response = requests.get("http://localhost:8000/api/entities")
if response.status_code == 200:
    entities = response.json()
    print(f"Found {len(entities)} entities")
    for e in entities[:3]:
        print(f"  - {e['name']} ({e['type']})")
else:
    print(f"Error: {response.status_code}")

# Test a simple search query instead
print("\nTesting simple search...")
response = requests.post("http://localhost:8000/api/search", json={
    "query": "Project Alpha",
    "limit": 5
})

if response.status_code == 200:
    results = response.json()
    print(f"Found {len(results)} results")
else:
    print(f"Error: {response.status_code} - {response.text}")