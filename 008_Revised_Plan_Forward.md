
# 008: Revised Plan for Production-Ready Vector Memory System

## 1. Executive Summary

This document outlines a detailed, phased plan to evolve the Smart-Meet-Lite system into a production-ready state. The strategy is rooted in a forensic analysis of the project's history, from initial setup (`001`) through the critical findings in state-tracking and entity resolution (`003`, `004`, `006`).

Our guiding principle is to **enhance, not reinvent**. We will build upon the functional but fragile architecture from the `004` milestone, systematically addressing the core issues of **performance, resilience, and query capability**. The previous implementation correctly identified the need for semantic state comparison but disabled it due to performance bottlenecks. This plan directly tackles that challenge by introducing batching and caching, re-enabling the system's core intelligence while ensuring stability.

The plan is broken into four distinct phases:
1.  **Foundational Stability:** Reinforce the storage layer and core processing logic.
2.  **Scalability & Intelligence:** Introduce advanced processing patterns for performance and accuracy.
3.  **Resilience & Production Hardening:** Implement comprehensive error handling and monitoring.
4.  **Integration & Verification:** Tie all components together and validate the end-to-end system.

## 2. Phase 1: Foundational Stability (Estimated: 4 Hours)

This phase focuses on strengthening the base components to support future enhancements. We will fix the disabled semantic comparison, add critical database indexes, and implement a foundational caching layer.

### 2.1. Task: Re-enable Semantic Comparison with Batching

**Problem:** The semantic state comparison, a cornerstone of the system's logic, was disabled (`# self.is_semantically_different(old, new)`) due to severe performance issues, as each comparison triggered a separate, slow LLM call.

**Solution:** We will create a new `LLMProcessor` class to encapsulate all interactions with the LLM. This class will feature a `compare_states_batch` method to process multiple state comparisons in a single, efficient call.

**File: `src/llm_processor.py` (New File)**
```python
import asyncio
from typing import List, Dict, Any, Tuple
from src.utils import llm_api_call # Assuming a utility for the actual API call

class LLMProcessor:
    """
    A centralized processor for all LLM interactions, featuring batching,
    caching, and resilience for state comparison and entity extraction.
    """
    def __init__(self, cache_layer):
        self.cache = cache_layer

    async def compare_states_batch(self, state_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Compares a batch of old/new state pairs using a single LLM call.
        """
        # Check cache first
        cached_results = [self.cache.get(f"compare:{pair[0]}_{pair[1]}") for pair in state_pairs]
        uncached_pairs = [pair for i, pair in enumerate(state_pairs) if cached_results[i] is None]
        
        if not uncached_pairs:
            return cached_results

        # Construct a single prompt for the batch
        prompt = self._build_batch_comparison_prompt(uncached_pairs)
        
        try:
            # This function would be responsible for the actual API call and parsing
            llm_response = await llm_api_call(prompt, model="gpt-4-turbo") 
            
            # Assume llm_response is a list of dicts with 'has_changes' and 'reason'
            results = self._parse_batch_response(llm_response, uncached_pairs)

            # Update cache
            for pair, result in zip(uncached_pairs, results):
                self.cache.set(f"compare:{pair[0]}_{pair[1]}", result)
            
            # Merge cached and new results
            final_results = []
            cache_iter = iter(cached_results)
            new_iter = iter(results)
            for res in cached_results:
                if res is not None:
                    final_results.append(res)
                else:
                    final_results.append(next(new_iter))
            return final_results

        except Exception as e:
            # Fallback to simple comparison on API failure
            return [self._simple_comparison(p[0], p[1]) for p in uncached_pairs]

    def _build_batch_comparison_prompt(self, pairs):
        # Logic to build a prompt that asks the LLM to evaluate all pairs at once
        return "..." 

    def _parse_batch_response(self, response, pairs):
        # Logic to parse the structured response from the LLM
        return [{"has_changes": True, "reason": "AI determined change."}] * len(pairs)

    def _simple_comparison(self, old_state, new_state):
        return {"has_changes": old_state != new_state, "reason": "Fallback comparison"}
```

### 2.2. Task: Implement Unified Caching Layer

**Problem:** The system lacks caching for expensive operations like LLM calls and database queries, leading to redundant computations and slow performance.

**Solution:** Create a `CacheLayer` that provides a simple key-value store with a TTL. This will be used by the `LLMProcessor` and `ProductionQueryEngine`.

**File: `src/cache.py` (New File)**
```python
import time
from typing import Dict, Any, Optional

class CacheLayer:
    """
    A simple in-memory cache with Time-To-Live (TTL) support.
    """
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and time.time() < self._ttl[key]:
            return self._cache[key]
        if key in self._cache:
            # Expired
            del self._cache[key]
            del self._ttl[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._cache[key] = value
        self._ttl[key] = time.time() + (ttl or self.default_ttl)
```

## 3. Phase 2: Scalability & Intelligence (Estimated: 6 Hours)

This phase enhances the system's core logic to handle complex queries and large inputs efficiently.

### 3.1. Task: Implement Production Query Engine

**Problem:** The current query mechanism is basic and does not synthesize information from both the vector database (for semantic context) and the relational database (for factual state data), as highlighted by the need for a `ProductionQueryEngine`.

**Solution:** We will implement `ProductionQueryEngine` to perform a multi-step query process:
1.  Use embeddings to find relevant meeting chunks (memories) from the vector DB.
2.  Extract key entities from these memories.
3.  Use the extracted entities to retrieve their latest, definitive states from the relational DB.
4.  Synthesize the information from both sources into a comprehensive answer.

**File: `src/query_engine.py` (New File)**
```python
class ProductionQueryEngine:
    def __init__(self, storage, embeddings, llm_processor, cache_layer):
        self.storage = storage
        self.embeddings = embeddings
        self.llm = llm_processor
        self.cache = cache_layer

    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Processes a complex query by searching both vector and relational stores.
        """
        # 1. Find relevant memories via semantic search
        query_embedding = self.embeddings.create(query)
        # Assuming storage has a method for vector search
        relevant_memories = self.storage.search_memories(query_embedding, top_k=5)

        # 2. Extract entities from the query and memories
        context_text = query + " " + " ".join([mem['content'] for mem in relevant_memories])
        # Assuming LLM can extract entities
        entities = await self.llm.extract_entities(context_text) 
        entity_names = [e['name'] for e in entities]

        # 3. Get current states for these entities from the relational DB
        entity_states = self.storage.get_current_states_for_entities(entity_names)

        # 4. Synthesize a final answer
        synthesis_prompt = self._build_synthesis_prompt(query, relevant_memories, entity_states)
        final_answer = await self.llm.generate_answer(synthesis_prompt)

        return {
            "answer": final_answer,
            "supporting_memories": [mem['id'] for mem in relevant_memories],
            "relevant_entities": entity_states
        }
    
    def _build_synthesis_prompt(self, query, memories, states):
        # Logic to build a rich prompt for the final answer generation
        return "..."
```

### 3.2. Task: Parallelize Large Meeting Ingestion

**Problem:** Processing meetings with a high number of entities and state changes can be extremely slow, blocking the ingestion pipeline.

**Solution:** In `MeetingProcessor`, we'll add a `process_meeting_parallel` method. For meetings with >20 entities, we will process state comparisons and entity resolutions in parallel batches.

**File: `src/meeting_processor.py` (Modification)**
```python
# Inside EnhancedMeetingProcessor class

async def process_meeting_with_context(self, extraction, meeting_id):
    # ... (existing logic) ...
    if len(extraction.entities) > 20:
        return await self.process_meeting_parallel(extraction, meeting_id)
    # ... (rest of the logic) ...

async def process_meeting_parallel(self, extraction, meeting_id):
    """
    Processes large meetings by batching and parallelizing state comparisons.
    """
    # ... (logic to group entities and states into batches) ...
    
    # Create tasks for each batch
    tasks = []
    for batch_of_state_pairs in batches:
        tasks.append(self.llm_processor.compare_states_batch(batch_of_state_pairs))
        
    # Run all batches in parallel
    batch_results = await asyncio.gather(*tasks)
    
    # ... (logic to flatten results and proceed with storing transitions) ...
    
    return {"status": "processed_in_parallel", ...}
```

## 4. Phase 3: Resilience & Production Hardening (Estimated: 3 Hours)

This phase makes the system robust against external failures (e.g., LLM API errors) and internal issues.

### 4.1. Task: Implement Centralized Error Handling

**Problem:** Errors from the LLM or database are not handled gracefully, potentially crashing the entire process.

**Solution:** Introduce a `with_recovery` decorator/context manager in the `LLMProcessor` that implements retry logic with exponential backoff and a final fallback to a simpler, deterministic method (e.g., string comparison) if the LLM remains unavailable.

**File: `src/llm_processor.py` (Modification)**
```python
# Inside LLMProcessor class

async def with_recovery(self, operation, fallback_method):
    """
    A wrapper to execute an LLM operation with retries and a fallback.
    """
    retries = 3
    delay = 1.0
    for i in range(retries):
        try:
            return await operation()
        except Exception as e:
            print(f"LLM operation failed (attempt {i+1}/{retries}): {e}")
            if i == retries - 1:
                print("LLM failed after all retries, using fallback.")
                return fallback_method()
            await asyncio.sleep(delay)
            delay *= 2 # Exponential backoff
            
# Example usage within the class
async def compare_states_batch(self, state_pairs):
    operation = lambda: self._execute_batch_comparison(state_pairs)
    fallback = lambda: [self._simple_comparison(p[0], p[1]) for p in state_pairs]
    return await self.with_recovery(operation, fallback)

async def _execute_batch_comparison(self, state_pairs):
    # ... (actual API call logic) ...
```

## 5. Phase 4: Integration & Verification (Estimated: 2 Hours)

This final phase ensures all new and modified components are correctly integrated into the API and validated with a new, comprehensive test suite.

### 5.1. Task: Update API and Main Application

**Problem:** The main application entry point (`run.py` or `api.py`) needs to be updated to initialize and use the new components (`LLMProcessor`, `ProductionQueryEngine`, `CacheLayer`).

**Solution:** Modify the application startup sequence to construct the new objects and inject them as dependencies into the processor and query endpoints.

**File: `run.py` (Modification)**
```python
# At startup
from src.cache import CacheLayer
from src.llm_processor import LLMProcessor
from src.query_engine import ProductionQueryEngine
# ... other imports

# Global objects
cache = CacheLayer()
llm_processor = LLMProcessor(cache)
storage = MemoryStorage() # Assuming this exists
embeddings = EmbeddingEngine() # Assuming this exists
query_engine = ProductionQueryEngine(storage, embeddings, llm_processor, cache)
meeting_processor = EnhancedMeetingProcessor(storage, ..., llm_processor)

# In API endpoints
@app.post("/api/query")
async def query(request: QueryRequest):
    return await query_engine.process_query(request.query)

@app.post("/api/ingest")
async def ingest(request: IngestRequest):
    # ...
    return await meeting_processor.process_meeting_with_context(...)
```

### 5.2. Task: Create Comprehensive Test Suite

**Problem:** Existing tests do not cover the new failure modes, batching logic, or the enhanced query capabilities.

**Solution:** Create a new test file, `test_production_system.py`, to validate the end-to-end functionality.

**File: `tests/test_production_system.py` (New File)**
```python
import pytest
from unittest.mock import patch, MagicMock

# ... imports for processor, query_engine, etc.

@pytest.mark.asyncio
async def test_semantic_comparison_in_batch():
    """Ensures batching works and returns correct change reasons."""
    # ... setup with mock LLMProcessor ...
    
@pytest.mark.asyncio
async def test_query_engine_synthesis():
    """Tests that the query engine pulls from both DBs and synthesizes a result."""
    # ... setup with mock storage and LLM ...

@pytest.mark.asyncio
async def test_llm_failure_fallback():
    """Ensures the system falls back to simple comparison when the LLM API fails."""
    with patch('src.llm_processor.llm_api_call', side_effect=Exception("API Error")):
        # ... run an ingestion and assert that it completes successfully using the fallback
```
