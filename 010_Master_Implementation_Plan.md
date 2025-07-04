
# 010: Master Implementation Plan

## 1. Guiding Principles

This document is the definitive, consolidated roadmap for evolving Smart-Meet-Lite to a production-ready state. It incorporates the forensic findings from `009` and the critical, low-level implementation details from user feedback. All previous plans are superseded.

Our principles are:
1.  **Restore First:** Our immediate priority is to restore the working baseline functionality of the `003` state, where the system correctly tracked entities and states, but to do so on a performant and reliable foundation.
2.  **Eliminate Over-Engineering:** We will remove the brittle, inaccurate regex-based inference from `processor_v2.py` and return to the original, simpler vision: use the LLM to compare a new state with a prior state.
3.  **Build for Resilience:** Every new component will be built with batching, caching, and intelligent fallbacks to handle real-world failures.

---

## PHASE 1: Foundational Performance & Resilience (Est: 3 Hours)

**Objective:** Forge a stable and fast foundation by fixing the database bottlenecks and making our LLM interactions robust.

### **Task 1.1: Implement Database Performance Enhancements**

**File:** `src/storage.py` (Modification)

*   **Action:** Add critical database indexes during initialization to prevent full table scans.

    ```python
    # In MemoryStorage.__init__ or a dedicated setup method
    self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_entity_states_entity_id ON entity_states(entity_id);")
    self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_state_transitions_entity_id ON state_transitions(entity_id);")
    self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_meeting_id ON memories(meeting_id);")
    self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_normalized_name ON entities(normalized_name);")
    self.db.commit()
    ```

*   **Action:** Implement batch database operations to minimize transaction overhead.

    ```python
    # Add new batch methods to MemoryStorage
    def save_entities_batch(self, entities: List[Entity]):
        # ... logic using executemany ...
    
    def save_transitions_batch(self, transitions: List[StateTransition]):
        # ... logic using executemany ...

    def get_entities_batch(self, entity_ids: List[str]) -> Dict[str, Entity]:
        # ... logic using a single SELECT ... IN ... query ...

    def get_states_batch(self, entity_ids: List[str]) -> Dict[str, EntityState]:
        # ... logic using a single SELECT ... IN ... query ...
    ```

### **Task 1.2: Create Resilient `LLMProcessor` and `CacheLayer`**

**File:** `src/cache.py` (New File)
*   **Action:** Create the `CacheLayer` class as defined in plan `009`.

**File:** `src/llm_processor.py` (New File)
*   **Action:** Create the `LLMProcessor` class.
*   **Action:** Implement the **model fallback chain** to handle OpenRouter API errors and model-specific requirements.

    ```python
    class LLMProcessor:
        MODELS = [
            "openai/gpt-4o-mini",
            "openai/gpt-4-turbo-preview",
            "openai/gpt-3.5-turbo",
            "mistralai/mixtral-8x7b"
        ]

        def __init__(self, llm_client: OpenAI, cache_layer: CacheLayer):
            # ...

        async def _call_with_fallback(self, prompt: str, **kwargs):
            for model in self.MODELS:
                try:
                    api_kwargs = kwargs.copy()
                    # Handle model-specific parameter incompatibility (e.g., response_format)
                    if "anthropic" in model or "mistral" in model:
                        if "response_format" in api_kwargs:
                            del api_kwargs["response_format"]
                    
                    # ... actual API call logic ...
                    return await self.client.chat.completions.create(model=model, ...)
                except Exception as e:
                    logger.warning(f"Model {model} failed: {e}. Trying next model.")
            raise Exception("All LLM models failed.")
    ```

*   **Action:** Implement `compare_states_batch` using the fallback logic.

---

## PHASE 2: Core Logic Remediation (Est: 4 Hours)

**Objective:** Restore the `003` baseline by gutting the flawed processor, fixing entity resolution, and ensuring data integrity.

### **Task 2.1: Gut and Rebuild `processor_v2.py`**

**File:** `src/processor_v2.py` (Major Refactoring)

*   **Action:** Inject `llm_processor` into the constructor.
*   **Action:** **Delete Dead Code.** Remove the loop processing `extraction.states` (lines ~210-217), which is always empty.
*   **Action:** **Remove Regex.** Delete `STATE_PATTERNS`, `ASSIGNMENT_PATTERNS`, `PROGRESS_PATTERNS`, and all associated inference methods (`_infer_states_from_patterns`, etc.).
*   **Action:** Rewrite `process_meeting_with_context` to use the new, simplified, LLM-centric pipeline.
*   **Action:** Replace `_create_comprehensive_transitions` with `_create_and_save_transitions_batch` which uses the `llm_processor` to get all state comparisons in a single, resilient, batched call.

### **Task 2.2: Fix Entity Resolution**

**File:** `src/processor_v2.py` (Modification)

*   **Action:** Ensure the shared `EntityResolver` instance is used for all entity matching. Remove any calls to simple string-matching functions like `_find_best_match`.

    ```python
    # In _process_relationships or other relevant methods
    # Replace fuzzy matching with the resolver
    resolved_entities = self.entity_resolver.resolve_entities([name1, name2])
    from_entity = resolved_entities.get(from_name)
    to_entity = resolved_entities.get(to_name)
    ```

### **Task 2.3: Implement State Tracking Validation**

**File:** `src/processor_v2.py` (Modification)

*   **Action:** Add a comprehensive validation method to be called at the end of processing. This method acts as a self-healing mechanism.

    ```python
    def _validate_state_tracking_completeness(self, entity_map, final_states, transitions):
        # 1. Check for entities that have a new state but no transition was created.
        # 2. If a transition is missing, log the error and auto-create a basic transition
        #    to ensure no state change is ever lost.
        # 3. Log all discrepancies to validation_metrics.
        pass
    ```

---

## PHASE 3: Advanced Capabilities (Est: 2 Hours)

**Objective:** Implement the enhanced query engine as originally envisioned.

### **Task 3.1: Implement `ProductionQueryEngine`**

**File:** `src/query_engine_v2.py` (Modification)

*   **Action:** Implement the `process_query` method with the correct, multi-step logic, paying special attention to using the new batch database methods.

    ```python
    async def process_query(self, query: str) -> Dict[str, Any]:
        # 1. Get relevant memories from vector search.
        relevant_memories = self.storage.search_memories(...)

        # 2. Collect all unique entity IDs from those memories.
        entity_ids = set()
        for mem in relevant_memories:
            entity_ids.update(mem.entity_mentions)
        
        # 3. **Critical Step:** Use BATCH operations to fetch all data from SQLite.
        entity_list = list(entity_ids)
        entities = self.storage.get_entities_batch(entity_list)
        states = self.storage.get_states_batch(entity_list)
        # transitions = self.storage.get_transitions_batch(entity_list) # If needed

        # 4. Construct a rich context from memories, entities, and their states.
        # 5. Call the LLM to synthesize the final, comprehensive answer.
        # 6. Return the structured result.
    ```

---

## PHASE 4: Verification (Est: 1 Hour)

**Objective:** Ensure all changes work together as expected.

### **Task 4.1: Update and Create Comprehensive Tests**

**File:** `tests/test_production_system.py` (New/Modification)

*   **Action:** Write targeted tests for:
    *   The `LLMProcessor`'s model fallback chain.
    *   The `storage` module's new batch operations.
    *   Correct usage of the `EntityResolver` in the processor.
    *   The `ProductionQueryEngine`'s multi-step, batch-fetching logic.
    *   The `_validate_state_tracking_completeness` self-healing mechanism.
