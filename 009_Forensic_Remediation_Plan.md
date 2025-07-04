
# 009: Forensic Remediation and Implementation Plan

## 1. Mandate: Achieve a Working Model

Our singular, laser-focused priority is to produce a reliable, functional system for meeting ingestion and state tracking. This plan is the direct result of a forensic, file-by-file analysis of the existing codebase. It is not based on prior documentation, but on the evidence of the code itself.

The core problem is a **fatal architectural disconnect**: the `extractor` produces a rich, LLM-derived output that the `processor` largely ignores in favor of brittle, inaccurate regex parsing. The system's intelligence, `_detect_semantic_changes`, was disabled due to a catastrophic performance design (N+1 LLM calls). This plan corrects that flaw.

We will **stop fighting the LLM** and instead leverage it correctly through targeted, batched, and resilient calls.

## 2. The Remediation Task List

This is a step-by-step, file-by-file plan to fix the system.

### **Task 1: Create the `LLMProcessor` (The Foundation)**

**Objective:** Centralize all LLM interactions into a single, resilient, and performant class. This is the cornerstone of the entire remediation.

**File: `src/llm_processor.py` (New File)**

```python
import asyncio
import json
from typing import List, Dict, Any, Tuple
from openai import OpenAI
from src.config import settings
import logging

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, llm_client: OpenAI, cache_layer):
        self.client = llm_client
        self.cache = cache_layer

    async def compare_states_batch(self, state_pairs: List[Tuple[Dict, Dict]]) -> List[Dict]:
        # Implementation with batch prompting, caching, and retry/fallback logic
        # as detailed in the original 008 plan.
        pass

    async def generate_transition_reasons_batch(self, transitions: List[Dict]) -> List[str]:
        # New method to generate reasons for all transitions in one call.
        pass

    # Add other required LLM tasks here (e.g., entity extraction if we refactor)
```

### **Task 2: Create the `CacheLayer`**

**Objective:** Implement the simple, in-memory cache to support the `LLMProcessor`.

**File: `src/cache.py` (New File)**

```python
# Code for CacheLayer as detailed in the 008 plan.
import time
from typing import Dict, Any, Optional

class CacheLayer:
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache and time.time() < self._ttl[key]:
            return self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._cache[key] = value
        self._ttl[key] = time.time() + (ttl or self.default_ttl)
```

### **Task 3: Refactor the API Startup**

**Objective:** Integrate the new `LLMProcessor` and `CacheLayer` into the application's lifecycle.

**File: `src/api.py` (Modification)**

```python
# ... imports
from .cache import CacheLayer
from .llm_processor import LLMProcessor

# ...

# Initialize components
storage = MemoryStorage()
embeddings = EmbeddingEngine()
cache = CacheLayer()

# ... LLM client setup ...

llm_processor = LLMProcessor(llm_client, cache)

# ...

# Pass llm_processor to the processor and query_engine
try:
    from .processor_v2 import EnhancedMeetingProcessor
    processor = EnhancedMeetingProcessor(storage, entity_resolver, embeddings, llm_processor)
    logger.info("Using production-ready processor_v2")
except ImportError:
    # ...

try:
    from .query_engine_v2 import ProductionQueryEngine
    query_engine = ProductionQueryEngine(storage, embeddings, entity_resolver, llm_processor)
    logger.info("Using production-ready query_engine_v2")
except ImportError:
    # ...
```

### **Task 4: Gut and Rebuild `processor_v2.py`**

**Objective:** This is the most critical step. We will remove the flawed regex-based inference and replace it with a streamlined, LLM-centric workflow.

**File: `src/processor_v2.py` (Major Refactoring)**

1.  **Remove Regex:** Delete the `STATE_PATTERNS`, `ASSIGNMENT_PATTERNS`, and `PROGRESS_PATTERNS` constants.
2.  **Delete Unused Methods:** Delete the now-obsolete methods: `_infer_states_from_patterns`, `_extract_progress_indicators`, `_extract_assignments`, and `_merge_state_information`.
3.  **Modify the Constructor:** Update `__init__` to accept the `llm_processor`.

    ```python
    def __init__(self, storage: Storage, entity_resolver: EntityResolver, embeddings: LocalEmbeddings, llm_processor: LLMProcessor):
        self.storage = storage
        self.entity_resolver = entity_resolver
        self.embeddings = embeddings
        self.llm_processor = llm_processor # New
        self.validation_metrics = {}
    ```

4.  **Rewrite `process_meeting_with_context`:** Simplify the main pipeline dramatically.

    ```python
    def process_meeting_with_context(self, extraction: ExtractionResult, meeting_id: str) -> Dict[str, Any]:
        logger.info(f"Processing meeting {meeting_id} with LLM-centric state tracking")
        entity_map = self._process_entities(extraction.entities, meeting_id)
        prior_states = self._fetch_all_prior_states(entity_map)
        
        # The ONLY source of current state is the extractor's output.
        current_states = self._extract_current_states(extraction, entity_map)
        
        # This becomes the core logic.
        transitions = self._create_and_save_transitions_batch(prior_states, current_states, meeting_id)
        
        # ... (relationship and memory processing remains similar) ...
        return { ... }
    ```

5.  **Rewrite `_create_comprehensive_transitions` to be `_create_and_save_transitions_batch`:**

    ```python
    async def _create_and_save_transitions_batch(self, prior_states, current_states, meeting_id):
        state_pairs_to_compare = []
        entity_ids_for_pairs = []

        for entity_id, current in current_states.items():
            prior = prior_states.get(entity_id)
            if self._is_meaningful_change(prior, current):
                state_pairs_to_compare.append((prior, current))
                entity_ids_for_pairs.append(entity_id)

        if not state_pairs_to_compare:
            return []

        # SINGLE BATCH CALL to the LLMProcessor
        comparison_results = await self.llm_processor.compare_states_batch(state_pairs_to_compare)

        transitions_to_create = []
        for i, result in enumerate(comparison_results):
            if result['has_changes']:
                entity_id = entity_ids_for_pairs[i]
                prior_state = state_pairs_to_compare[i][0]
                to_state = state_pairs_to_compare[i][1]
                
                transition = StateTransition(
                    entity_id=entity_id,
                    from_state=prior_state,
                    to_state=to_state,
                    changed_fields=result.get('changed_fields', list(to_state.keys())),
                    reason=result.get('reason', 'State updated.'), # Temporarily use reason from compare
                    meeting_id=meeting_id
                )
                transitions_to_create.append(transition)
        
        if transitions_to_create:
            self.storage.save_transitions(transitions_to_create)
            # We can add a batch reason generation call here later if needed.

        return transitions_to_create
    ```

6.  **Delete `_detect_field_changes`, `_simple_field_comparison`, and `_detect_semantic_changes`:** This logic is now entirely encapsulated within the `LLMProcessor`.

### **Task 5: Refine the Extractor's Schema (Optional but Recommended)**

**Objective:** Make the initial extraction more robust by simplifying the schema.

**File: `src/extractor_enhanced.py` (Modification)**

*   Review the `json_schema` and identify non-critical, complex nested objects that can be simplified or removed. The goal is to reduce the chance of the LLM producing invalid JSON. Focus on flattening the structure where possible. For example, instead of deep nesting for `detailed_minutes`, a simpler list of key points might suffice for the processor's needs.

## 3. Expected Outcome

Upon completion of this plan, the ingestion pipeline will be:

*   **Robust:** It will correctly use the LLM for its core intelligence and handle API failures gracefully.
*   **Performant:** The N+1 problem will be eliminated through batching, resolving the timeout issues.
*   **Maintainable:** The logic will be centralized and simplified, removing the brittle and unmaintainable regex forest.
*   **Effective:** State tracking will finally work as intended, accurately capturing the evolution of entities discussed in meetings.

This plan directly addresses the root causes of failure discovered during the forensic analysis. It provides a clear, actionable path to a working model.
