#!/usr/bin/env python3
"""Ingest all meeting files from the data folder."""

import os
import json
import time
import requests
from pathlib import Path

# Meeting transcripts to ingest
meeting_files = [
    {
        "file": "data/BRV Day One Readiness and UAT Coordination.eml",
        "title": "BRV Day One Readiness and UAT Coordination"
    },
    {
        "file": "data/Comprehensive Testing Strategy And Logistics Planning.eml", 
        "title": "Comprehensive Testing Strategy And Logistics Planning"
    },
    {
        "file": "data/Comprehensive UAT Planning and Readiness Coordination.eml",
        "title": "Comprehensive UAT Planning and Readiness Coordination"
    },
    {
        "file": "data/Coordinating Roles and Testing Across Functions.eml",
        "title": "Coordinating Roles and Testing Across Functions"
    },
    {
        "file": "data/Dashboard Preparation and Data Integration Planning.eml",
        "title": "Dashboard Preparation and Data Integration Planning"
    },
    {
        "file": "data/Executive Presentation Preparation and Coordination Plan.eml",
        "title": "Executive Presentation Preparation and Coordination Plan"
    },
    {
        "file": "data/Executive Testing Dashboard and Resource Planning.eml",
        "title": "Executive Testing Dashboard and Resource Planning"
    },
    {
        "file": "data/Standardizing Testing Data Coordination and Reporting.eml",
        "title": "Standardizing Testing Data Coordination and Reporting"
    },
    {
        "file": "data/UAT Preparation Tracking Dashboard and Reporting.eml",
        "title": "UAT Preparation Tracking Dashboard and Reporting"
    },
    {
        "file": "data/UAT Readiness and Business Process Dashboarding.eml",
        "title": "UAT Readiness and Business Process Dashboarding"
    }
]

# Also include the sample transcript
sample_transcript = """
Sarah: Hey team, let's discuss the mobile app redesign project status.
Mike: Sure! I've been working on the API optimization. We've improved response times by 40%.
Lisa: Great! I've completed the navigation mockups and dark mode designs.
Tom: The new navigation structure looks good. When can we start implementation?
Sarah: Let's aim to have the first version ready by Friday. Mike, can you help Tom with the API integration?
Mike: Absolutely. I'll also look into the caching solution we discussed.
"""

print("Ingesting All Meeting Files")
print("=" * 60)

# First, ingest the sample transcript
print("\n1. Ingesting sample transcript...")
try:
    response = requests.post(
        "http://localhost:8000/api/ingest",
        json={
            "title": "Mobile App Redesign - Status Update",
            "transcript": sample_transcript
        }
    )
    if response.status_code == 200:
        result = response.json()
        print(f"   ✓ Success! Entities: {result['entity_count']}, Memories: {result['memory_count']}")
    else:
        print(f"   ✗ Failed: {response.status_code} - {response.text[:100]}")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Now ingest EML files (these would need to be parsed first)
print("\n2. Processing EML files...")
print("   Note: EML files need email parsing - skipping for now")
print("   These contain meeting minutes that would need extraction")

# Test some queries
print("\n" + "=" * 60)
print("Testing Queries After Ingestion")
print("=" * 60)

test_queries = [
    "What is the status of mobile app redesign?",
    "Who is working on API optimization?",
    "What did Lisa complete?",
    "List all projects",
    "Show me recent decisions"
]

for query in test_queries:
    print(f"\nQuery: {query}")
    try:
        response = requests.post(
            "http://localhost:8000/api/query",
            json={"query": query}
        )
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'No answer')
            # Truncate long answers
            if len(answer) > 150:
                answer = answer[:150] + "..."
            print(f"Answer: {answer}")
        else:
            print(f"Error: {response.status_code}")
    except Exception as e:
        print(f"Error: {e}")

# Check entity count
print("\n" + "=" * 60)
print("System Statistics")
print("=" * 60)

try:
    response = requests.get("http://localhost:8000/api/entities")
    if response.status_code == 200:
        entities = response.json()
        print(f"Total entities in system: {len(entities)}")
        
        # Count by type
        entity_types = {}
        for entity in entities:
            entity_type = entity.get('type', 'unknown')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        print("\nEntities by type:")
        for entity_type, count in sorted(entity_types.items()):
            print(f"  - {entity_type}: {count}")
except Exception as e:
    print(f"Error getting entities: {e}")

print("\n✅ Ingestion test complete!")