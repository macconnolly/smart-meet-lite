#!/usr/bin/env python3
"""Test script to verify all query types work correctly."""

import asyncio
import json
import logging
from src.storage import MemoryStorage
from src.embeddings import EmbeddingEngine
from src.entity_resolver import EntityResolver
from src.query_engine_v2 import ProductionQueryEngine
from openai import OpenAI
from src.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_queries():
    """Test various query types."""
    # Initialize components
    storage = MemoryStorage()
    embeddings = EmbeddingEngine()
    entity_resolver = EntityResolver(storage, embeddings)
    
    # Initialize OpenAI client (not used in updated version but needed for constructor)
    llm_client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    query_engine = ProductionQueryEngine(storage, embeddings, entity_resolver, llm_client)
    
    # Test queries
    test_queries = [
        # Timeline queries
        "How did the authentication service progress over time?",
        "Show me the timeline for Project Nexus",
        
        # Status queries
        "What's the current status of the API gateway?",
        "Where are we with the mobile app development?",
        
        # Blocker queries
        "What's blocking the frontend team?",
        "Show me all current blockers",
        
        # Ownership queries
        "Who owns the authentication service?",
        "Who is responsible for Project Nexus?",
        
        # Analytics queries
        "How many features are in progress?",
        "Show me the metrics for Q4",
        
        # Relationship queries
        "What depends on the authentication service?",
        "Show dependencies for the API gateway",
        
        # Search queries
        "Find all mentions of database migration",
        "Search for discussions about security"
    ]
    
    results = []
    for query in test_queries:
        logger.info(f"\nTesting query: {query}")
        try:
            result = await query_engine.process_query(query)
            logger.info(f"✓ Success: {result.intent.intent_type}")
            logger.info(f"  Answer preview: {result.answer[:100]}...")
            logger.info(f"  Confidence: {result.confidence}")
            results.append({
                "query": query,
                "status": "success",
                "intent": result.intent.intent_type,
                "confidence": result.confidence
            })
        except Exception as e:
            logger.error(f"✗ Failed: {type(e).__name__}: {e}")
            results.append({
                "query": query,
                "status": "failed",
                "error": str(e)
            })
    
    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    logger.info(f"\n\nSummary: {successful}/{len(test_queries)} queries successful")
    
    # Save results
    with open("query_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    asyncio.run(test_queries())