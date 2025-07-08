#!/usr/bin/env python3
"""Direct test of query response generation methods to verify OpenRouter integration."""

import json
from src.query_engine_v2 import ProductionQueryEngine, QueryContext, QueryIntent
from datetime import datetime

# Create a minimal query engine instance just to test the methods
class TestQueryEngine:
    def __init__(self):
        # Import the methods we need to test
        from src.query_engine_v2 import ProductionQueryEngine
        self._call_openrouter_api = ProductionQueryEngine._call_openrouter_api.__get__(self, ProductionQueryEngine)
        self._get_proxies = ProductionQueryEngine._get_proxies.__get__(self, ProductionQueryEngine)
        self._generate_timeline_response = ProductionQueryEngine._generate_timeline_response.__get__(self, ProductionQueryEngine)
        self._generate_status_response = ProductionQueryEngine._generate_status_response.__get__(self, ProductionQueryEngine)
        self._generate_blocker_response = ProductionQueryEngine._generate_blocker_response.__get__(self, ProductionQueryEngine)
        self._generate_ownership_response = ProductionQueryEngine._generate_ownership_response.__get__(self, ProductionQueryEngine)
        self._generate_analytics_response = ProductionQueryEngine._generate_analytics_response.__get__(self, ProductionQueryEngine)
        self._generate_relationship_response = ProductionQueryEngine._generate_relationship_response.__get__(self, ProductionQueryEngine)
        self._generate_search_response = ProductionQueryEngine._generate_search_response.__get__(self, ProductionQueryEngine)

def test_response_methods():
    """Test each response generation method."""
    engine = TestQueryEngine()
    
    # Create mock context
    context = QueryContext(
        query="Test query",
        intent=QueryIntent(intent_type="test", entities=[], filters={}, time_range=None, aggregation=None),
        entities=[],
        memories=[],
        state_history={},
        transitions={},
        relationships={},
        metadata={}
    )
    
    print("Testing Query Response Generation Methods\n" + "="*50)
    
    # Test 1: Timeline Response
    print("\n1. Testing Timeline Response...")
    timeline_data = [{
        "entity": "Project Alpha",
        "type": "project",
        "timeline": [
            {
                "date": "2024-01-15T10:00:00",
                "from_state": {"status": "planned"},
                "to_state": {"status": "in_progress"},
                "changes": ["status"],
                "reason": "Project kickoff"
            }
        ]
    }]
    
    try:
        response = engine._generate_timeline_response(timeline_data, context)
        print(f"✓ Timeline Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
        print(f"  - Confidence value: {response.get('confidence', 'N/A')}")
    except Exception as e:
        print(f"✗ Timeline Response: Failed - {type(e).__name__}: {e}")
    
    # Test 2: Status Response
    print("\n2. Testing Status Response...")
    status_data = [{
        "entity": "API Gateway",
        "type": "feature",
        "current_state": {"status": "in_progress", "progress": 75},
        "last_updated": "2024-01-20T14:30:00",
        "recent_changes": []
    }]
    
    try:
        response = engine._generate_status_response(status_data, context)
        print(f"✓ Status Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
    except Exception as e:
        print(f"✗ Status Response: Failed - {type(e).__name__}: {e}")
    
    # Test 3: Blocker Response
    print("\n3. Testing Blocker Response...")
    blocker_data = [{
        "entity": "Frontend Module",
        "type": "feature",
        "current_blockers": ["Waiting for API specs", "Design review pending"],
        "resolution_history": []
    }]
    
    try:
        response = engine._generate_blocker_response(blocker_data, context)
        print(f"✓ Blocker Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
    except Exception as e:
        print(f"✗ Blocker Response: Failed - {type(e).__name__}: {e}")
    
    # Test 4: Ownership Response
    print("\n4. Testing Ownership Response...")
    ownership_data = [{
        "entity": "Authentication Service",
        "type": "feature",
        "current_owner": "Alice Johnson",
        "ownership_history": []
    }]
    
    try:
        response = engine._generate_ownership_response(ownership_data, context)
        print(f"✓ Ownership Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
    except Exception as e:
        print(f"✗ Ownership Response: Failed - {type(e).__name__}: {e}")
    
    # Test 5: Analytics Response
    print("\n5. Testing Analytics Response...")
    analytics_data = {
        "summary": {
            "total_entities": 15,
            "by_type": {"project": 3, "feature": 12},
            "by_status": {"in_progress": 8, "blocked": 2, "completed": 5}
        }
    }
    
    try:
        response = engine._generate_analytics_response(analytics_data, context)
        print(f"✓ Analytics Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
    except Exception as e:
        print(f"✗ Analytics Response: Failed - {type(e).__name__}: {e}")
    
    # Test 6: Relationship Response
    print("\n6. Testing Relationship Response...")
    relationship_data = [{
        "entity": "Database Layer",
        "type": "component",
        "relationships": {
            "depends_on": [{"entity": "Schema Design", "type": "task", "since": "2024-01-10"}],
            "blocks": [],
            "works_with": [],
            "owns": []
        }
    }]
    
    try:
        response = engine._generate_relationship_response(relationship_data, context)
        print(f"✓ Relationship Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
    except Exception as e:
        print(f"✗ Relationship Response: Failed - {type(e).__name__}: {e}")
    
    # Test 7: Search Response
    print("\n7. Testing Search Response...")
    search_data = [{
        "content": "We discussed the migration strategy in detail",
        "meeting": "Architecture Review",
        "date": "2024-01-18T10:00:00",
        "score": 0.95,
        "entities": ["Migration Project"]
    }]
    
    try:
        response = engine._generate_search_response(search_data, context)
        print(f"✓ Search Response: Success")
        print(f"  - Has 'answer': {'answer' in response}")
        print(f"  - Has 'confidence': {'confidence' in response}")
    except Exception as e:
        print(f"✗ Search Response: Failed - {type(e).__name__}: {e}")
    
    print("\n" + "="*50)
    print("Test completed!")

if __name__ == "__main__":
    from src.config import settings
    
    # Check if API key is configured
    if not settings.openrouter_api_key or settings.openrouter_api_key == "sk-or-replace-me":
        print("ERROR: OpenRouter API key not configured!")
        print("Please set OPENROUTER_API_KEY in your .env file")
    else:
        print(f"Using OpenRouter model: {settings.clean_openrouter_model}")
        print(f"API Key configured: {settings.openrouter_api_key[:10]}...")
        test_response_methods()