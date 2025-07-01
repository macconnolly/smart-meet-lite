#!/usr/bin/env python3
"""Stress test ingestion to reproduce threading issues."""

import requests
import time

# Multiple meeting transcripts to ingest rapidly
meetings = [
    {
        "title": "Sprint Planning - Week 1",
        "transcript": """
        Sarah: Let's plan our sprint. We need to focus on the authentication module.
        Mike: I'll take the OAuth integration. Should take about 3 days.
        Lisa: I'll work on the UI components for login and registration.
        Tom: I can handle the database schema for user management.
        """
    },
    {
        "title": "API Design Review",
        "transcript": """
        Mike: I've designed the REST API endpoints for our service.
        Tom: The endpoints look good. What about rate limiting?
        Mike: Good point. I'll add rate limiting middleware.
        Sarah: Make sure we have proper error handling and logging.
        """
    },
    {
        "title": "UI/UX Review Session", 
        "transcript": """
        Lisa: Here are the new mockups for the dashboard.
        Sarah: The color scheme works well with our brand.
        Tom: Can we add more data visualization components?
        Lisa: Yes, I'll incorporate charts for the analytics section.
        """
    },
    {
        "title": "Performance Optimization Meeting",
        "transcript": """
        Mike: We're seeing slow response times on the search endpoint.
        Tom: I'll add database indexes for the commonly queried fields.
        Mike: I'll also implement caching for frequent searches.
        Sarah: Let's set a target of 200ms response time.
        """
    },
    {
        "title": "Security Review",
        "transcript": """
        Tom: We need to review our security measures.
        Mike: I've implemented JWT tokens with refresh tokens.
        Sarah: What about SQL injection prevention?
        Tom: All queries use parameterized statements.
        """
    }
]

print("Stress Testing Ingestion")
print("=" * 60)

success_count = 0
error_count = 0
errors = []

for i, meeting in enumerate(meetings, 1):
    print(f"\n{i}. Ingesting: {meeting['title']}")
    try:
        response = requests.post(
            "http://localhost:8000/api/ingest",
            json={
                "title": meeting['title'],
                "transcript": meeting['transcript']
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Success! Entities: {result['entity_count']}, Memories: {result['memory_count']}")
            success_count += 1
        else:
            print(f"   ✗ Failed: {response.status_code}")
            error_count += 1
            errors.append({
                "meeting": meeting['title'],
                "status": response.status_code,
                "error": response.text[:200]
            })
            
        # Small delay between requests
        time.sleep(0.5)
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        error_count += 1
        errors.append({
            "meeting": meeting['title'],
            "error": str(e)
        })

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Total meetings: {len(meetings)}")
print(f"Successful: {success_count}")
print(f"Failed: {error_count}")

if errors:
    print("\nErrors encountered:")
    for error in errors:
        print(f"- {error['meeting']}: {error.get('error', error.get('status'))}")

# Final entity count
try:
    response = requests.get("http://localhost:8000/api/entities")
    if response.status_code == 200:
        entities = response.json()
        print(f"\nTotal entities in system: {len(entities)}")
except:
    pass