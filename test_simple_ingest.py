#!/usr/bin/env python3
"""Simple test to debug ingestion issues."""

import requests
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

def test_simple_ingest():
    """Test with a very simple meeting transcript."""
    
    # Very simple transcript
    transcript = """
    Team meeting for Project Alpha.
    
    Sarah: I'll be leading Project Alpha. It's currently in the planning phase.
    John: Great! When will it start?
    Sarah: We'll begin development next week.
    """
    
    print("Testing simple ingestion...")
    print(f"Transcript:\n{transcript}\n")
    
    try:
        response = requests.post(
            f"{API_BASE}/api/ingest",
            json={
                "title": "Simple Test Meeting",
                "transcript": transcript,
                "date": datetime.now().isoformat()
            },
            timeout=120.0
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Meeting ID: {data['id']}")
            print(f"Entities found: {data['entity_count']}")
            print(f"Memories extracted: {data['memory_count']}")
            print(f"Summary: {data.get('summary', 'No summary')}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Exception: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple_ingest()