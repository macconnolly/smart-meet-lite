#!/usr/bin/env python3
"""Debug script to isolate Smart-Meet Lite issues."""

import json
import logging
import traceback
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all imports work correctly."""
    print("\n=== Testing Imports ===")
    try:
        from src.embeddings import EmbeddingEngine
        print("✓ EmbeddingEngine import OK")
        
        from src.storage import MemoryStorage
        print("✓ MemoryStorage import OK")
        
        from src.extractor import MemoryExtractor
        print("✓ MemoryExtractor import OK")
        
        from src.query_engine import QueryEngine
        print("✓ QueryEngine import OK")
        
        from src.processor import EntityProcessor
        print("✓ EntityProcessor import OK")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_embedding_generation():
    """Test embedding generation without threading."""
    print("\n=== Testing Embedding Generation ===")
    try:
        from src.embeddings import EmbeddingEngine
        
        engine = EmbeddingEngine()
        print("✓ EmbeddingEngine initialized")
        
        # Test single embedding
        test_text = "Mobile App Redesign Project"
        embedding = engine.encode(test_text)
        print(f"✓ Generated embedding for '{test_text}': shape={embedding.shape}")
        
        # Test multiple embeddings
        texts = ["Sarah", "Mike", "API optimization", "billing system"]
        embeddings = engine.encode(texts)
        print(f"✓ Generated batch embeddings: shape={embeddings.shape}")
        
        return True
    except Exception as e:
        print(f"✗ Embedding generation failed: {e}")
        traceback.print_exc()
        return False

def test_database_operations():
    """Test database operations without threading."""
    print("\n=== Testing Database Operations ===")
    try:
        from src.storage import MemoryStorage
        from src.models import Entity, EntityType
        import numpy as np
        
        storage = MemoryStorage()
        print("✓ Storage initialized")
        
        # Test entity creation
        test_entity = Entity(
            name="Test Project",
            type=EntityType.PROJECT,
            attributes={"status": "active"}
        )
        
        # Save entity
        storage.save_entities([test_entity])
        print(f"✓ Saved entity: {test_entity.name}")
        
        # Test retrieval
        retrieved = storage.get_entity_by_name("Test Project")
        print(f"✓ Retrieved entity: {retrieved.name if retrieved else 'None'}")
        
        # Test embedding update
        if retrieved:
            test_embedding = np.random.rand(384).astype(np.float32)
            storage.update_entity_embedding(retrieved.id, test_embedding)
            print("✓ Updated entity embedding")
        
        return True
    except Exception as e:
        print(f"✗ Database operation failed: {e}")
        traceback.print_exc()
        return False

def test_llm_query_parsing():
    """Test LLM query parsing with detailed logging."""
    print("\n=== Testing LLM Query Parsing ===")
    try:
        from src.query_engine import QueryEngine
        from src.storage import MemoryStorage
        from src.embeddings import EmbeddingEngine
        from src.config import settings
        import openai
        import httpx
        
        # Test direct LLM call first
        print(f"Model: {settings.openrouter_model}")
        print(f"Base URL: {settings.openrouter_base_url}")
        
        # Create client with SSL disabled
        http_client = httpx.Client(verify=False)
        client = openai.OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Smart-Meet Lite Debug",
            },
            http_client=http_client
        )
        
        # Test simple query
        test_prompt = """Parse this query and return JSON with the following structure:
{
  "intent_type": "status",
  "entities": ["mobile app redesign"],
  "filters": {},
  "aggregation": null
}

Just return the JSON, nothing else."""
        
        response = client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": test_prompt},
                {"role": "user", "content": "What is the status of mobile app redesign?"}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        raw_content = response.choices[0].message.content
        print(f"✓ LLM responded. Raw content length: {len(raw_content)}")
        print(f"Raw content preview: {raw_content[:200]}")
        
        # Try parsing
        try:
            # Handle potential markdown wrapping
            if "```json" in raw_content:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', raw_content, re.DOTALL)
                if json_match:
                    raw_content = json_match.group(1)
                    print("✓ Extracted JSON from markdown block")
            
            parsed = json.loads(raw_content.strip())
            print(f"✓ Parsed JSON successfully: {parsed}")
        except json.JSONDecodeError as je:
            print(f"✗ JSON parsing failed: {je}")
            print(f"Content that failed to parse: '{raw_content}'")
        
        return True
        
    except Exception as e:
        print(f"✗ LLM query parsing failed: {e}")
        traceback.print_exc()
        return False

def test_full_query_flow():
    """Test the full query flow with entity resolution."""
    print("\n=== Testing Full Query Flow ===")
    try:
        from src.query_engine import QueryEngine
        from src.storage import MemoryStorage
        from src.embeddings import EmbeddingEngine
        
        storage = MemoryStorage()
        embeddings = EmbeddingEngine()
        
        # Initialize query engine
        query_engine = QueryEngine(storage, embeddings)
        print("✓ QueryEngine initialized")
        
        # Test a simple query
        test_query = "What is the status of the mobile app redesign?"
        print(f"Testing query: '{test_query}'")
        
        result = query_engine.answer_query(test_query)
        print(f"✓ Query completed. Result type: {result.result_type}")
        print(f"  Success: {result.success}")
        if not result.success:
            print(f"  Error: {result.error}")
        
        return True
        
    except Exception as e:
        print(f"✗ Full query flow failed: {e}")
        traceback.print_exc()
        return False

def test_ingestion_without_threading():
    """Test ingestion with threading disabled."""
    print("\n=== Testing Ingestion Without Threading ===")
    try:
        from src.processor import EntityProcessor
        from src.storage import MemoryStorage
        import threading
        
        # Monkey patch to disable threading
        original_thread_start = threading.Thread.start
        def no_op_start(self):
            print("  [Thread start disabled for testing]")
            # Run the target function directly instead of in a thread
            if hasattr(self, '_target') and self._target:
                self._target(*self._args, **self._kwargs)
        
        threading.Thread.start = no_op_start
        
        storage = MemoryStorage()
        processor = EntityProcessor(storage)
        print("✓ EntityProcessor initialized")
        
        # Create test extraction result
        from src.models import ExtractionResult, Memory
        test_extraction = ExtractionResult(
            memories=[
                Memory(
                    content="Sarah is leading the mobile app redesign project",
                    entity_mentions=["Sarah", "mobile app redesign project"]
                )
            ],
            entities=[
                {"name": "Sarah", "type": "person"},
                {"name": "mobile app redesign project", "type": "project"}
            ],
            relationships=[
                {"from": "Sarah", "to": "mobile app redesign project", "type": "owns"}
            ],
            topics=["project planning"],
            participants=["Sarah"],
            summary="Project planning meeting"
        )
        
        # Process extraction
        result = processor.process_extraction(test_extraction, "test-meeting-123")
        print(f"✓ Processed extraction: {result['entities_created']} entities created")
        
        # Restore original threading
        threading.Thread.start = original_thread_start
        
        return True
        
    except Exception as e:
        print(f"✗ Ingestion test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all debug tests."""
    print("Smart-Meet Lite Debug Script")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Embedding Generation", test_embedding_generation),
        ("Database Operations", test_database_operations),
        ("LLM Query Parsing", test_llm_query_parsing),
        ("Full Query Flow", test_full_query_flow),
        ("Ingestion Without Threading", test_ingestion_without_threading)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, success in results if success)
    print(f"\nTotal: {total_passed}/{len(tests)} tests passed")

if __name__ == "__main__":
    main()