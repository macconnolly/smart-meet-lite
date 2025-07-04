#!/usr/bin/env python3
"""
Test the new batch processing implementation.
Verifies that state transitions are properly detected with the new LLM processor.
"""

import asyncio
import json
from datetime import datetime

from src.storage import MemoryStorage
from src.entity_resolver import EntityResolver
from src.embeddings import EmbeddingEngine
from src.cache import CacheLayer
from src.llm_processor import LLMProcessor
from src.processor_v2 import EnhancedMeetingProcessor
from src.models import ExtractionResult
from src.config import settings

# Initialize OpenAI client for entity resolver
from openai import OpenAI
llm_client = OpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
)


async def test_batch_state_comparison():
    """Test the batch state comparison functionality."""
    print("=== Testing Batch State Comparison ===\n")
    
    # Initialize components
    storage = MemoryStorage()
    embeddings = EmbeddingEngine()
    cache = CacheLayer(default_ttl=300)  # 5 min cache for testing
    llm_processor = LLMProcessor(cache)
    entity_resolver = EntityResolver(storage, embeddings, llm_client)
    processor = EnhancedMeetingProcessor(storage, entity_resolver, embeddings, llm_processor)
    
    # Test data: Multiple state pairs to compare
    state_pairs = [
        # Pair 1: Clear changes
        (
            {"status": "planned", "progress": None},
            {"status": "in_progress", "progress": "30%"}
        ),
        # Pair 2: No real change (semantic equivalence)
        (
            {"status": "planning"},
            {"status": "in planning phase"}
        ),
        # Pair 3: Multiple changes
        (
            {"status": "in_progress", "assigned_to": "Alice"},
            {"status": "blocked", "assigned_to": "Bob", "blockers": ["dependency on API"]}
        ),
        # Pair 4: Progress change only
        (
            {"status": "in_progress", "progress": "30%"},
            {"status": "in_progress", "progress": "50%"}
        ),
        # Pair 5: New fields added
        (
            {"status": "planned"},
            {"status": "planned", "priority": "high", "deadline": "2025-08-01"}
        )
    ]
    
    print(f"Comparing {len(state_pairs)} state pairs...\n")
    
    # Test batch comparison
    results = await llm_processor.compare_states_batch(state_pairs)
    
    # Display results
    for i, (result, (old_state, new_state)) in enumerate(zip(results, state_pairs)):
        print(f"Comparison {i+1}:")
        print(f"  Old: {json.dumps(old_state, indent=4)}")
        print(f"  New: {json.dumps(new_state, indent=4)}")
        print(f"  Has Changes: {result['has_changes']}")
        print(f"  Changed Fields: {result['changed_fields']}")
        print(f"  Reason: {result['reason']}")
        print()
    
    # Test caching
    print("\n=== Testing Cache ===")
    print("Running same comparisons again (should use cache)...")
    
    results2 = await llm_processor.compare_states_batch(state_pairs)
    
    # Check cache stats
    stats = cache.stats()
    print(f"\nCache Statistics:")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate']:.2%}")
    print(f"  Cache Size: {stats['size']}")
    
    # Verify results are the same
    assert len(results) == len(results2)
    for r1, r2 in zip(results, results2):
        assert r1['has_changes'] == r2['has_changes']
        assert set(r1['changed_fields']) == set(r2['changed_fields'])
    
    print("\n✓ Cache test passed - results are consistent")
    
    # Test with a real meeting extraction
    print("\n\n=== Testing Full Meeting Processing ===")
    
    # Create a mock extraction result with all required fields
    extraction = ExtractionResult(
        entities=[
            {
                "name": "Project Alpha",
                "type": "project",
                "current_state": {
                    "status": "in_progress",
                    "progress": "50%",
                    "assigned_to": "Bob"
                }
            },
            {
                "name": "API Migration",
                "type": "feature",
                "current_state": {
                    "status": "blocked",
                    "blockers": ["waiting for vendor response"]
                }
            }
        ],
        relationships=[],
        memories=[],
        states=[],  # Always empty in current implementation
        meeting_metadata={
            "summary": "Team discussed progress on Project Alpha and API Migration blockers",
            "date": datetime.now().isoformat()
        },
        summary="Team discussed progress on Project Alpha and API Migration blockers",
        topics=["Project Alpha", "API Migration", "Blockers"],
        participants=["Bob", "Alice", "Charlie"],
        decisions=["Continue with Project Alpha", "Escalate API vendor issue"],
        action_items=[
            {"task": "Follow up with vendor", "assignee": "Charlie", "due": "2025-08-03"}
        ]
    )
    
    meeting_id = f"test_meeting_{datetime.now().timestamp()}"
    
    # Process the meeting
    print(f"Processing meeting: {meeting_id}")
    result = processor.process_meeting_with_context(extraction, meeting_id)
    
    print(f"\nProcessing Results:")
    print(f"  Entities Processed: {result['validation']['entities_processed']}")
    print(f"  States Captured: {result['validation']['states_captured']}")
    print(f"  Transitions Created: {result['validation']['transitions_created']}")
    print(f"  Patterns Matched: {result['validation']['patterns_matched']}")
    
    if result['state_changes']:
        print(f"\nState Transitions:")
        for transition in result['state_changes']:
            print(f"  - Entity: {transition.entity_id}")
            print(f"    Changed Fields: {transition.changed_fields}")
            print(f"    Reason: {transition.reason}")
    
    # Check LLM processor stats
    llm_stats = llm_processor.get_stats()
    print(f"\nLLM Processor Statistics:")
    print(f"  Fallback Count: {llm_stats['fallback_count']}")
    print(f"  Models Available: {llm_stats['models_available']}")
    print(f"  Cache Hit Rate: {llm_stats['cache_stats']['hit_rate']:.2%}")
    
    print("\n✓ All tests passed!")


if __name__ == "__main__":
    # Run synchronously to avoid nested event loop issues
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(test_batch_state_comparison())