#!/usr/bin/env python3
"""Test ingestion with threading disabled."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import threading
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Disable threading for testing
original_thread_start = threading.Thread.start
def no_op_start(self):
    print("[Threading disabled - running synchronously]")
    if hasattr(self, '_target') and self._target:
        self._target(*self._args, **self._kwargs)

threading.Thread.start = no_op_start

# Now run the test
import requests

test_transcript = """
Sarah: Hey team, let's discuss the mobile app redesign project status.
Mike: Sure! I've been working on the API optimization. We've improved response times by 40%.
Lisa: Great! I've completed the navigation mockups and dark mode designs.
Tom: The new navigation structure looks good. When can we start implementation?
Sarah: Let's aim to have the first version ready by Friday. Mike, can you help Tom with the API integration?
Mike: Absolutely. I'll also look into the caching solution we discussed.
"""

# Test ingestion
print("Testing ingestion with threading disabled...")
response = requests.post(
    "http://localhost:8000/api/ingest",
    json={
        "title": "Mobile App Redesign - Test Without Threading",
        "transcript": test_transcript
    }
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✓ Ingestion successful!")
    print(f"Response: {response.json()}")
else:
    print(f"✗ Ingestion failed: {response.text}")

# Restore threading
threading.Thread.start = original_thread_start
print("\n[Threading restored]")