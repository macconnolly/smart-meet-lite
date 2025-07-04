#!/usr/bin/env python3
"""Debug script to test ingestion and identify issues."""

import requests
import json
import logging
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test transcript
TEST_TRANSCRIPT = """
John Smith (Product Manager): Good morning everyone. Let's discuss the Smart Analytics Dashboard project status.

Sarah Chen (Engineering Lead): Thanks John. The backend API development is progressing well. We've completed the data pipeline integration and the real-time analytics engine is now in testing phase.

Mike Johnson (Designer): On the UI side, we've finalized the dashboard wireframes and the interactive charts are about 70% complete. We're facing some challenges with the responsive design for mobile devices.

John Smith: What's blocking the mobile design?

Mike Johnson: The main issue is fitting all the analytics widgets on smaller screens without losing functionality. We need to prioritize which metrics are most important for mobile users.

Sarah Chen: I suggest we implement a collapsible panel system. Users can expand the metrics they need on mobile.

John Smith: That sounds like a good approach. When can we have a working prototype?

Sarah Chen: If Mike can finalize the mobile designs by Friday, we can have a prototype ready by next Wednesday.

Mike Johnson: I'll prioritize the mobile layouts and have them ready by Friday.

John Smith: Great. Any other blockers we should discuss?

Sarah Chen: We need to finalize the authentication system. Should we use OAuth or implement our own?

John Smith: Let's go with OAuth for now. It's more secure and saves development time.

Sarah Chen: Agreed. I'll assign that to the backend team.

John Smith: Excellent. Let's reconvene next Monday to review progress. Thanks everyone.
"""

def test_config():
    """Test configuration loading."""
    logger.info("=== Testing Configuration ===")
    try:
        from src.config import settings
        logger.info(f"Model configured: {settings.openrouter_model}")
        logger.info(f"Clean model name: {settings.clean_openrouter_model}")
        logger.info(f"API Key present: {'Yes' if settings.openrouter_api_key else 'No'}")
        logger.info(f"API Key prefix: {settings.openrouter_api_key[:20] if settings.openrouter_api_key else 'None'}")
        return True
    except Exception as e:
        logger.error(f"Config test failed: {e}")
        return False

def test_extractor():
    """Test the extractor directly."""
    logger.info("\n=== Testing Extractor Directly ===")
    try:
        from src.extractor_enhanced import EnhancedMeetingExtractor
        from src.config import settings
        import httpx
        from openai import OpenAI
        
        # Create HTTP client
        http_client = httpx.Client(
            verify=settings.ssl_verify,
            timeout=30.0
        )
        
        # Create LLM client
        llm_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Smart-Meet Lite Test"
            },
            http_client=http_client
        )
        
        # Create extractor
        extractor = EnhancedMeetingExtractor(llm_client)
        
        # Test extraction
        logger.info("Calling extractor.extract()...")
        result = extractor.extract(TEST_TRANSCRIPT, "test-meeting-001")
        
        logger.info(f"Extraction result:")
        logger.info(f"  - Memories: {len(result.memories)}")
        logger.info(f"  - Entities: {len(result.entities)}")
        logger.info(f"  - Summary: {result.summary[:100] if result.summary else 'None'}...")
        logger.info(f"  - Metadata: {result.meeting_metadata}")
        
        return True
    except Exception as e:
        logger.error(f"Extractor test failed: {e}", exc_info=True)
        return False

def test_api_ingestion():
    """Test the API ingestion endpoint."""
    logger.info("\n=== Testing API Ingestion ===")
    
    api_url = "http://localhost:8000/api/ingest"
    
    payload = {
        "title": "Smart Analytics Dashboard Status Meeting",
        "transcript": TEST_TRANSCRIPT,
        "date": datetime.now().isoformat()
    }
    
    try:
        logger.info(f"Sending POST request to {api_url}")
        response = requests.post(api_url, json=payload, timeout=60)
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Success! Meeting ID: {data.get('id')}")
            logger.info(f"  - Memory count: {data.get('memory_count')}")
            logger.info(f"  - Entity count: {data.get('entity_count')}")
            logger.info(f"  - Participants: {data.get('participants')}")
            logger.info(f"  - Topics: {data.get('topics')}")
            return data
        else:
            logger.error(f"Failed with status {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        logger.error("Could not connect to API. Is the server running?")
        logger.error("Try running: make run")
        return None
    except Exception as e:
        logger.error(f"API test failed: {e}", exc_info=True)
        return None

def test_api_query(meeting_id=None):
    """Test the API query endpoint."""
    logger.info("\n=== Testing API Query ===")
    
    api_url = "http://localhost:8000/api/query"
    
    test_queries = [
        "What is the status of the Smart Analytics Dashboard?",
        "What are the current blockers?",
        "Who is responsible for the mobile design?"
    ]
    
    for query in test_queries:
        logger.info(f"\nTesting query: '{query}'")
        
        payload = {"query": query}
        
        try:
            response = requests.post(api_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"  Answer: {data.get('answer', 'No answer')[:200]}...")
                logger.info(f"  Confidence: {data.get('confidence', 0)}")
                logger.info(f"  Intent type: {data.get('intent', {}).get('type', 'unknown')}")
            else:
                logger.error(f"  Failed with status {response.status_code}")
                logger.error(f"  Response: {response.text}")
                
        except Exception as e:
            logger.error(f"  Query failed: {e}")

def main():
    """Run all tests."""
    logger.info("Starting ingestion debug tests...")
    
    # Test 1: Configuration
    if not test_config():
        logger.error("Configuration test failed. Stopping.")
        return
    
    # Test 2: Direct extractor test
    if not test_extractor():
        logger.error("Extractor test failed. Check logs above.")
    
    # Test 3: API ingestion
    result = test_api_ingestion()
    
    # Test 4: API query (if ingestion succeeded)
    if result:
        test_api_query(result.get('id'))
    
    logger.info("\n=== Tests Complete ===")

if __name__ == "__main__":
    main()