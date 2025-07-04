# 004: State Tracking and Timeline Query Failures - Detailed Implementation Report

## Previous Context (from 003)

In update 003, we discovered that entity resolution was fundamentally broken due to architectural issues:
- **EntityProcessor** had its own basic fuzzy matcher (80% threshold) 
- **EntityResolver** had sophisticated multi-strategy resolution (75% threshold) with vector search and LLM fallback
- These were **not connected** - EntityProcessor never used EntityResolver
- This caused false positives: "vendor quotes for infrastructure" incorrectly matched to "vendor issues" at 86% similarity
- ~20% of relationships failed to create because entities weren't properly resolved

## What We Actually Did

### Phase 1: Connected EntityResolver to EntityProcessor

**Problem**: EntityProcessor and QueryEngine were each creating their own EntityResolver instances with different configurations.

**Implementation**:
1. **Modified `src/api.py`** to create a single shared EntityResolver:
   ```python
   # Line 15: Added imports
   from .entity_resolver import EntityResolver
   import httpx
   
   # Lines 40-57: Created shared components
   http_client = httpx.Client(verify=False)  # For corporate SSL bypass
   llm_client = OpenAI(
       api_key=settings.openrouter_api_key,
       base_url=settings.openrouter_base_url,
       default_headers={
           "HTTP-Referer": "http://localhost:8000",
           "X-Title": "Smart-Meet Lite"
       },
       http_client=http_client
   )
   
   # Create ONE EntityResolver used by both processor and query engine
   entity_resolver = EntityResolver(
       storage=storage,
       embeddings=embeddings,
       llm_client=llm_client,
       use_llm=settings.entity_resolution_use_llm
   )
   
   # Pass shared resolver to both
   processor = EntityProcessor(storage, entity_resolver)
   query_engine = QueryEngine(storage, embeddings, entity_resolver)
   ```

2. **Modified `src/processor.py`**:
   - Changed constructor to accept EntityResolver parameter
   - Deleted the broken `_find_best_match` method (lines 165-187)
   - Created new `_resolve_entity_names` method that uses EntityResolver
   - Updated `_process_relationships` to use the new resolution
   - Added auto-creation of deliverable entities for action items

3. **Modified `src/query_engine.py`**:
   - Removed duplicate EntityResolver creation
   - Uses the shared instance from api.py

4. **Modified `src/entity_resolver.py`**:
   - Added `use_llm` parameter to control LLM usage
   - Updated resolve logic to respect this flag

### Phase 2: Clean Reset Due to Historical Bad Data

**Discovery**: During testing, we found that entities had been incorrectly extracted/stored from the beginning:
- LLM was truncating entity names: "vendor quotes for infrastructure" → "vendor quotes"
- This wasn't our code changes - it was happening in the original extraction

**Decision**: Clean reset of all data rather than trying to fix corrupted historical data.

**Implementation**:
1. Created `clean_reset.py` script that:
   - Backed up existing database
   - Deleted all data from SQLite and Qdrant
   - Preserved schema integrity
   
2. Re-ingested test data with improved system

### Phase 3: Testing Revealed New Critical Issue

**What We Expected**: With entity resolution fixed, the system would work properly.

**What Actually Happened**:
1. Entity extraction: ✅ Working (full names, no truncation)
2. Entity resolution: ✅ Working (correct matches, no false positives)
3. Relationships: ✅ Working (11 created successfully)
4. Entity states: ✅ 102 states saved
5. State transitions: ❌ **Only 16 transitions created** (should be 100+)
6. Timeline queries: ❌ **500 errors or empty results**

## Root Cause Analysis of State Tracking Failure

### The Code Path
1. `processor.py` → `process_extraction()` → `_process_state_changes()`
2. For each entity with a state, it:
   - Gets the previous state from storage
   - Compares old vs new state
   - **Only creates a transition if they differ**

### The Problem
The state comparison is failing. Looking at the logs:
```
ERROR - Failed to process entity: {'name': 'Alice', 'type': 'person', 
        'attributes': {'role': 'Product Manager'}, 
        'current_state': {'status': 'active'}}. 
Error: table entity_states has no column named confidence
```

Initially this was a schema issue (missing confidence column), but even after fixing that, transitions aren't being created.

### Why Timeline Queries Fail
```python
# query_engine.py - _answer_timeline_query()
timeline = self.storage.get_entity_timeline(entity.id)
# Returns data from state_transitions table
# But with only 16 transitions, most entities have NO timeline data
```

The entire timeline feature depends on the `state_transitions` table being populated when states change between meetings.

## Specific Examples of What Should Work But Doesn't

### Example 1: Project State Evolution
**Meeting 1**: "The mobile app redesign project is in planning phase"
**Meeting 2**: "The mobile app redesign project is now in progress"
**Expected**: State transition from planned → in_progress
**Actual**: New state created, but NO transition recorded

### Example 2: Blocker Lifecycle  
**Meeting 2**: "API optimization is blocked on database migration"
**Meeting 3**: "Database migration complete, API optimization unblocked"
**Expected**: Transition from blocked → in_progress
**Actual**: States updated, but NO transition showing the unblocking

### Example 3: Timeline Query
**Query**: "How did the API optimization project progress over time?"
**Expected**: Timeline showing planned → in_progress → blocked → in_progress → completed
**Actual**: 500 error because `get_entity_timeline()` returns empty data

## Current State of the Codebase

### What's Working
- Entity extraction with full names
- Entity resolution using sophisticated strategies
- Relationship creation and tracking
- Basic state storage (current state of each entity)
- Vector search and semantic queries

### What's Broken
- State change detection between meetings
- Timeline data generation
- Complex queries about progress/blockers
- Any query that depends on historical state data

### Database State
- `entities` table: 64 entities ✅
- `entity_states` table: 102 states ✅
- `state_transitions` table: 16 transitions ❌ (should be ~100)
- `entity_relationships` table: 11 relationships ✅

## Next Steps - Detailed Implementation Plan

### 1. Debug State Change Detection (2 hours)
```python
# In processor.py _process_state_changes()
# Add comprehensive logging:
logger.debug(f"Comparing states for entity {entity_id}")
logger.debug(f"Previous state: {json.dumps(previous_state, indent=2)}")
logger.debug(f"New state: {json.dumps(new_state, indent=2)}")
logger.debug(f"States equal: {previous_state == new_state}")
logger.debug(f"Comparison details: {DeepDiff(previous_state, new_state)}")
```

### 2. Fix State Comparison Logic (1 hour)
The current comparison might be:
- Comparing JSON strings vs dictionaries
- Including timestamps in comparison
- Missing normalization of state data

### 3. Implement State Inference (3 hours)
```python
def _infer_state_from_context(self, entity_name: str, transcript_segment: str) -> Optional[Dict]:
    """Detect implicit state changes from context."""
    patterns = {
        'in_progress': ['now working on', 'started', 'in progress', 'begun'],
        'completed': ['finished', 'completed', 'done', 'delivered'],
        'blocked': ['blocked', 'waiting on', 'stuck', 'can\'t proceed'],
    }
    # Implementation to detect these patterns
```

### 4. Create Comprehensive Tests (2 hours)
```python
# test_state_transitions.py
def test_explicit_state_change():
    # Ingest meeting 1: "Project X is planned"
    # Ingest meeting 2: "Project X is in progress"
    # Assert: state_transitions table has 1 entry for Project X
    
def test_state_inference():
    # Ingest: "We're now working on Project Y"
    # Assert: Project Y state = in_progress
```

## Why This Matters

Without state transitions:
- **No historical data**: Can't answer "how did X change over time?"
- **No progress tracking**: Can't see project evolution
- **No blocker analysis**: Can't identify what got stuck and when
- **No trend analysis**: Can't spot patterns in how work flows

This is the core business intelligence feature that makes Smart-Meet more than just a search engine.

## Actual Code That Needs Fixing

```python
# processor.py - Current broken code around line 380
def _process_state_changes(self, 
                          entity: Entity,
                          new_state: Dict[str, Any],
                          meeting_id: str) -> Optional[StateTransition]:
    # Get previous state
    previous_state = self.storage.get_entity_current_state(entity.id)
    
    # This comparison is likely broken
    if previous_state != new_state:  # <-- THIS IS THE PROBLEM
        # Create transition
        transition = StateTransition(...)
        self.storage.save_transitions([transition])
```

The fix involves understanding:
1. What format is `previous_state`? (JSON string? Dict?)
2. What format is `new_state`? (Dict from extraction)
3. Are we comparing the right fields?
4. Should we ignore certain fields (like timestamps)?

## Summary

We successfully fixed entity resolution by connecting EntityResolver to EntityProcessor, but discovered that state tracking has been broken all along. The system creates entity states but fails to detect changes between meetings, resulting in empty timeline data and failed business intelligence queries. The fix requires debugging the state comparison logic and implementing state inference from context.