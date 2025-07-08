#!/usr/bin/env python3
"""Test Phase 1: String Formatting Fix for % characters in entity data."""

import os
import sys
import json
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.query_engine_v2 import ProductionQueryEngine, QueryContext, QueryIntent
from src.storage import MemoryStorage
from src.embeddings import EmbeddingEngine
from src.entity_resolver import EntityResolver
from openai import OpenAI
from src.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_string_formatting_with_percent():
    """Test that the query engine handles entity data with % characters correctly."""
    print("\n=== Testing Phase 1: String Formatting Fix ===\n")
    
    # Initialize components
    storage = MemoryStorage()
    embeddings = EmbeddingEngine()
    entity_resolver = EntityResolver(storage, embeddings)
    llm_client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    query_engine = ProductionQueryEngine(storage, embeddings, entity_resolver, llm_client)
    
    # Test case 1: Entity name with % character
    print("Test 1: Timeline query with % in entity name")
    print("-" * 50)
    
    test_timeline_data = [{
        "entity": "50% Milestone Project",
        "type": "project",
        "timeline": [{
            "date": "2025-01-01T10:00:00",
            "from_state": None,
            "to_state": {"status": "planned", "progress": "0%"},
            "changes": ["status"],
            "reason": "Project initiated with 50% completion target"
        }, {
            "date": "2025-01-05T14:00:00",
            "from_state": {"status": "planned", "progress": "0%"},
            "to_state": {"status": "in_progress", "progress": "25%"},
            "changes": ["status", "progress"],
            "reason": "Development started, 25% complete"
        }]
    }]
    
    # Create test context
    context = QueryContext(
        query="What is the timeline for 50% Milestone Project?",
        intent=QueryIntent(intent_type="timeline", entities=["50% Milestone Project"]),
        entities=[],
        memories=[],
        state_history={},
        transitions={},
        relationships={},
        metadata={}
    )
    
    try:
        response = query_engine._generate_timeline_response(test_timeline_data, context)
        print("✅ Success! Response generated without error:")
        print(f"Answer: {response.get('answer', 'No answer')[:200]}...")
        print(f"Confidence: {response.get('confidence', 0)}")
    except Exception as e:
        print(f"❌ Failed with error: {type(e).__name__}: {e}")
        return False
    
    # Test case 2: Blocker data with % character
    print("\n\nTest 2: Blocker query with % in blocker description")
    print("-" * 50)
    
    test_blocker_data = [{
        "entity": "Performance Testing",
        "type": "task",
        "current_blockers": [
            "CPU usage exceeds 90% threshold",
            "Memory usage at 85% capacity"
        ],
        "resolution_history": []
    }]
    
    context.query = "What are the blockers for Performance Testing?"
    context.intent.intent_type = "blocker"
    
    try:
        response = query_engine._generate_blocker_response(test_blocker_data, context)
        print("✅ Success! Response generated without error:")
        print(f"Answer: {response.get('answer', 'No answer')[:200]}...")
        print(f"Confidence: {response.get('confidence', 0)}")
    except Exception as e:
        print(f"❌ Failed with error: {type(e).__name__}: {e}")
        return False
    
    # Test case 3: Status data with % character
    print("\n\nTest 3: Status query with % in status data")
    print("-" * 50)
    
    test_status_data = [{
        "entity": "Q4 Sales Target",
        "type": "goal",
        "current_state": {
            "status": "in_progress",
            "achievement": "75%",
            "target": "100% of $1M goal"
        },
        "last_updated": datetime.now().isoformat(),
        "recent_changes": [{
            "date": datetime.now().isoformat(),
            "change": "Progress increased from 50% to 75%",
            "fields": ["achievement"]
        }]
    }]
    
    context.query = "What is the status of Q4 Sales Target?"
    context.intent.intent_type = "status"
    
    try:
        response = query_engine._generate_status_response(test_status_data, context)
        print("✅ Success! Response generated without error:")
        print(f"Answer: {response.get('answer', 'No answer')[:200]}...")
        print(f"Confidence: {response.get('confidence', 0)}")
    except Exception as e:
        print(f"❌ Failed with error: {type(e).__name__}: {e}")
        return False
    
    # Test case 4: Analytics data with % character
    print("\n\nTest 4: Analytics query with % in metrics")
    print("-" * 50)
    
    test_analytics_data = {
        "summary": {
            "total_entities": 10,
            "by_status": {
                "completed": 5,
                "in_progress": 3,
                "blocked": 2
            }
        },
        "metrics": {
            "completion_rate": "50%",
            "on_time_delivery": "80%",
            "resource_utilization": "95%"
        }
    }
    
    context.query = "What are the project metrics?"
    context.intent.intent_type = "analytics"
    
    try:
        response = query_engine._generate_analytics_response(test_analytics_data, context)
        print("✅ Success! Response generated without error:")
        print(f"Answer: {response.get('answer', 'No answer')[:200]}...")
        print(f"Confidence: {response.get('confidence', 0)}")
    except Exception as e:
        print(f"❌ Failed with error: {type(e).__name__}: {e}")
        return False
    
    print("\n\n=== Phase 1 Testing Complete ===")
    print("✅ All tests passed! String formatting fix is working correctly.")
    return True

if __name__ == "__main__":
    # Check if we have required environment variables
    if not settings.openrouter_api_key:
        print("Error: OPENROUTER_API_KEY not set in environment")
        sys.exit(1)
    
    # Run the test
    success = test_string_formatting_with_percent()
    sys.exit(0 if success else 1)