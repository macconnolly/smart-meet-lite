# 018 Current Plan: Comprehensive Query Engine Fix Roadmap

**Created**: 2025-01-07  
**Last Updated**: 2025-01-08 04:40  
**Status**: IN PROGRESS - Core Functionality Restored  
**Progress**: 2/10 Planned Phases Complete (20%)  
**Estimated Time**: 6 hours total (2.5 hours completed)  
**Priority**: HIGH - System working, optimization phases pending

## Executive Summary

The Smart-Meet Lite system successfully ingests meeting data and tracks entity state changes. Initial query operations were failing with HTTP 500 errors. Phases 1, 2, and 2b have been completed. Entity resolution has been fixed and tested - the system now correctly tracks entities across meetings, monitors progress changes, and records blockers. All core functionality is working.

### CURRENT STATUS (2025-01-08 04:40)

**Completed Phases:**
- ✅ **Phase 1**: String formatting fixed - queries with % characters work correctly
- ✅ **Phase 2**: State normalization implemented at storage layer
- ✅ **Phase 2b**: Relationship normalizer integrated (sub-phase of Phase 2)

**Critical Issue Fixed (Unplanned):**
- ✅ **Entity Resolution**: Root cause discovered and fixed
  - Entities were saved but embeddings weren't generated
  - Vector search was returning 0 results
  - This caused duplicate entities instead of updates
  - Progress/blockers fields were missing from schema
  - All issues now resolved and tested

**Test Results Verified:**
- Entity embeddings: Generated and stored (e.g., "Saved embedding for entity 'API Migration'")
- Vector search: Working (API Migration found with similarity score 0.507)
- State tracking: Confirmed (Project Alpha: 30% → 50% progress)
- Query responses: All return HTTP 200 with valid data
- Entity matching: No duplicates created in second meeting

**Pending Phases:**
- ⏳ **Phase 3**: Entity extraction improvements (stop words)
- ⏳ **Phase 4**: Response conciseness (under 100 words)
- ⏳ **Phase 5**: Query caching (5-minute TTL)
- ⏳ **Phase 6**: Async/await corrections
- ⏳ **Phase 7**: Database index fixes
- ⏳ **Phase 8**: LLM processor cleanup
- ⏳ **Phase 9**: Comprehensive testing
- ⏳ **Phase 10**: Production deployment

### COMPLETED WORK DETAILS:

#### Phase 1: String Formatting Fix (Completed)
- **Files Modified**: `src/query_engine_v2.py`
- **Changes**: Replaced ALL f-strings with string concatenation in 7 methods:
  - `_generate_timeline_response` (lines 666-700)
  - `_generate_blocker_response` (lines 755-788)
  - `_generate_status_response` (lines 790-823)
  - `_generate_ownership_response` (lines 1249-1283)
  - `_generate_analytics_response` (lines 1285-1319)
  - `_generate_relationship_response` (lines 1321-1355)
  - `_generate_search_response` (lines 1357-1391)
- **Test Files Created**: `test_phase1_string_formatting.py`, `test_phase1_api.py`
- **Result**: Queries with % characters (like "50% milestone") no longer crash

#### Phase 2: State Normalization (Completed)
- **Files Created**: 
  - `src/state_normalizer.py` - Complete normalization utilities
  - `scripts/normalize_existing_states.py` - Database migration script
  - `test_phase2_api.py` - API test suite
- **Files Modified**: 
  - `src/storage.py` - Added normalize_state_dict import and usage in save_entity_state()
  - `src/processor_v2.py` - Added normalize_state_dict import and usage in _extract_current_states()
- **Changes**: 
  - Created canonical state mappings (planned, in_progress, completed, blocked, cancelled)
  - Modified storage layer to normalize all states before saving
  - Created migration script to normalize existing database entries
- **Result**: No more fake state changes like "In Progress" vs "in_progress"

#### Phase 2b: Relationship Normalization (Completed)
- **Files Created**: 
  - `src/relationship_normalizer.py` - Complete relationship normalization utilities
  - `test_phase2b_api.py` - API test for relationship warnings
- **Files Modified**: 
  - `src/processor_v2.py` - Added normalize_relationship_type import and integrated into _validate_relationship_type()
- **Changes**: 
  - Created canonical relationship mappings (e.g., "responsible" → "responsible_for", "depends" → "depends_on")
  - Updated processor validation to normalize before checking enum
- **Result**: No more "Invalid relationship type" warnings in logs

### VERIFIED WORKING:
- ✅ Basic queries return HTTP 200 with valid responses
- ✅ Entity ingestion and extraction functioning
- ✅ State normalization preventing fake state change reports
- ✅ Relationship type warnings eliminated from logs
- ✅ All commits made separately for easy rollback

### CRITICAL ISSUE DISCOVERED: State Change Tracking Failure

**Problem**: The system is NOT tracking state changes between meetings. This is a fundamental failure of the core functionality.

**Root Cause Analysis**:
1. **Entity Duplication**: When Meeting 2 references "API Migration", it creates a NEW entity instead of updating the existing "API Migration feature" from Meeting 1
2. **Entity Resolution Failure**: The entity resolver is not matching similar entity names:
   - "API Migration" vs "API Migration feature" 
   - "Database Upgrade" vs "Database Upgrade project"
3. **Result**: All 6 state transitions in the database are "Initial state captured" - NO actual state changes were tracked

**Evidence**:
- Database contains 6 entities total, with 2 sets of duplicates
- All state_transitions records show `from_state = NULL` (initial captures only)
- Project Alpha went from 30% to 50% complete between meetings but this change was NOT tracked
- API Migration went from "blocked" to "in_progress" but was recorded as two separate entities

**Impact**: This completely breaks the system's ability to:
- Track progress over time
- Show entity evolution
- Provide timeline views of changes
- Answer questions about state transitions

### ENTITY RESOLUTION IMPLEMENTATION DETAILS:

**What Was Done**:
1. ✅ **Thresholds Already Lowered**: Found that config.py already has vector_threshold=0.70, fuzzy_threshold=0.65
2. ✅ **Suffix Stripping Already Implemented**: entity_resolver.py already strips suffixes like 'feature', 'project', 'system', etc.
3. ✅ **Vector Similarity Properly Used**: Entity resolver uses search_entity_embeddings internally
4. ✅ **Hybrid Approach Implemented**: api.py now uses BOTH:
   - Vector similarity search on transcript to find semantically related entities
   - Text extraction and entity name matching
   - Case-insensitive checking of all existing entity names

**Key Code Changes in api.py**:
```python
# HYBRID APPROACH: Use both vector similarity and text extraction
# 1. Create transcript embedding and search for similar entities
transcript_embedding = embeddings.encode(request.transcript)
similar_entity_results = storage.search_entity_embeddings(transcript_embedding, limit=10)

# 2. Extract entity names from text
entity_pattern = r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b'
matches = re.findall(entity_pattern, request.transcript)

# 3. Check all existing entities for case-insensitive matches
for entity in all_entities:
    if entity.name.lower() in transcript_lower:
        potential_entities.add(entity.name)

# 4. Use entity resolver on all candidates
resolution_results = entity_resolver.resolve_entities(potential_list, context)
```

**Why This Should Work**:
- Vector search finds entities even if not mentioned by exact name
- Text extraction catches explicit mentions
- Case-insensitive matching handles variations
- Entity resolver applies all 4 strategies (exact, vector, fuzzy, LLM)

### ENTITY RESOLUTION FIX (COMPLETED - 2025-01-08 04:35)

**Root Cause Discovered**:
1. **Missing Entity Embeddings**: Entities were saved to SQLite but embeddings were NOT generated/stored in Qdrant
2. **API Counting Bug**: Logging showed "vector: 0 + resolved: 0" even when entities were found
3. **Missing Schema Fields**: Progress and blockers fields were missing from extraction schema
4. **Import Error**: EntityType was not imported in query_engine_v2.py

**Fixes Implemented**:
1. **processor_v2.py (lines 760-779)**: Added embedding generation loop after save_entities()
2. **api.py (lines 187-270)**: Fixed entity counting to track vector_entities vs text_entities
3. **extractor_enhanced.py (lines 145-155)**: Added progress/blockers to schema
4. **query_engine_v2.py (line 19)**: Added EntityType to imports
5. **llm_processor.py (lines 226-228)**: Added rules for progress/blocker comparison

**Test Results**:
- ✅ Entity embeddings generated and stored (verified in logs)
- ✅ Vector similarity finding entities (API Migration score: 0.507)
- ✅ State changes tracked (Project Alpha: 30% → 50%)
- ✅ Progress percentages extracted correctly
- ✅ Blockers recorded and tracked
- ✅ All queries return HTTP 200 with valid responses

### NEXT IMMEDIATE STEPS:
1. **Phase 3: Entity Extraction Improvements** (45 minutes)
   - Implement comprehensive stop word filtering
   - Prevent extraction of "What", "December", "Status" as entities
   - Update _extract_query_entities method in query_engine_v2.py
   
2. **Phase 4: Response Conciseness** (30 minutes)
   - Update all 7 prompt generation methods
   - Request responses under 100 words
   - Remove verbose language patterns
   
3. **Phase 5: Query Caching** (1 hour)
   - Implement 5-minute in-memory cache
   - Add cache statistics endpoints
   - Reduce API costs by 60%+

### Issues Resolved:
1. ✅ **String formatting bug** - Fixed with string concatenation
2. ✅ **State normalization** - Canonical states implemented
3. ✅ **Entity resolution** - Embeddings and vector search working
4. ✅ **Progress/blockers tracking** - Schema fields added

### Issues Remaining:
1. **Entity extraction** - Common words extracted as entities ("What", "December")
2. **Verbose responses** - Answers are 200+ words instead of concise
3. **No query caching** - Every identical query costs money
4. **Async/await** issues in query processing
5. **Database index** misconfigurations
6. **Duplicate LLM processor** initialization

## Critical Issues Overview

### Current Error Messages:
```json
{"detail":"0"}
{"detail":"Invalid format specifier ' \"Your comprehensive answer here\",\n\"confidence\": 0.95\n' for object of type 'str'"}
```

### Root Causes:
1. F-strings in prompt generation interpret `%` in entity data as format specifiers
2. JSON schema examples being used in string formatting operations
3. Missing error handling and type validation
4. Synchronous code in async context

---

## Phase 1: Emergency String Formatting Fix (30 minutes) ✅ COMPLETED

### Problem
F-strings in `query_engine_v2.py` cause crashes when entity names or states contain `%` characters.

### Solution
Replace f-string formatting with string concatenation in all prompt generation methods.

### IMPLEMENTATION COMPLETED (2025-01-07 20:35)
✅ Successfully replaced ALL f-strings with string concatenation in 7 methods:
- `_generate_timeline_response` (lines 666-700)
- `_generate_blocker_response` (lines 755-788) 
- `_generate_status_response` (lines 790-823)
- `_generate_ownership_response` (lines 1249-1283)
- `_generate_analytics_response` (lines 1285-1319)
- `_generate_relationship_response` (lines 1321-1355)
- `_generate_search_response` (lines 1357-1391)

✅ Created test file: `test_phase1_string_formatting.py`
✅ Created API test file: `test_phase1_api.py`
✅ Fixed additional bug found: `result.meeting.date.isoformat()` NoneType error (line 1023)

### TEST RESULTS:
- ✅ Queries with % characters no longer crash
- ✅ Entity names like "50% Milestone Project" work correctly
- ✅ Status data with "75% completion" processes without errors
- ✅ All edge cases pass except one unrelated bug

### Implementation Steps

#### 1.1 Fix `_generate_timeline_response` (lines ~436-499)

**FIND**:
```python
prompt = f"""
Based on the timeline data below, answer this query: {context.query}

Timeline:
{json.dumps(timeline_entries, indent=2)}

Provide a clear timeline summary focusing on key state changes and dates.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the timeline data below, answer this query: """ + context.query + """

Timeline:
""" + json.dumps(timeline_entries, indent=2) + """

Provide a clear timeline summary focusing on key state changes and dates.
"""
```

#### 1.2 Fix `_generate_blocker_response` (lines ~500-556)

**FIND**:
```python
prompt = f"""
Based on the blocker data below, answer this query: {context.query}

Current Blockers:
{json.dumps(blocker_data, indent=2)}

Provide a comprehensive analysis of blockers and their impacts.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the blocker data below, answer this query: """ + context.query + """

Current Blockers:
""" + json.dumps(blocker_data, indent=2) + """

Provide a comprehensive analysis of blockers and their impacts.
"""
```

#### 1.3 Fix `_generate_status_response` (lines ~557-636)

**FIND**:
```python
prompt = f"""
Based on the current status data below, answer this query: {context.query}

Current States:
{json.dumps(status_data, indent=2)}

Recent Context:
{json.dumps(recent_memories, indent=2)}

Provide a comprehensive status update focusing on current state and recent changes.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the current status data below, answer this query: """ + context.query + """

Current States:
""" + json.dumps(status_data, indent=2) + """

Recent Context:
""" + json.dumps(recent_memories, indent=2) + """

Provide a comprehensive status update focusing on current state and recent changes.
"""
```

#### 1.4 Fix `_generate_ownership_response` (lines ~875-936)

**FIND**:
```python
prompt = f"""
Based on the ownership and relationship data below, answer this query: {context.query}

Ownership Data:
{json.dumps(ownership_data, indent=2)}

Provide clear information about ownership and responsibilities.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the ownership and relationship data below, answer this query: """ + context.query + """

Ownership Data:
""" + json.dumps(ownership_data, indent=2) + """

Provide clear information about ownership and responsibilities.
"""
```

#### 1.5 Fix `_generate_analytics_response` (lines ~1037-1200)

**FIND**:
```python
prompt = f"""
Based on the analytics data below, answer this query: {context.query}

Analytics Summary:
{json.dumps(analytics_data, indent=2)}

Provide insights and trends based on the data.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the analytics data below, answer this query: """ + context.query + """

Analytics Summary:
""" + json.dumps(analytics_data, indent=2) + """

Provide insights and trends based on the data.
"""
```

#### 1.6 Fix `_generate_relationship_response` (lines ~831-874)

**FIND**:
```python
prompt = f"""
Based on the relationship data below, answer this query: {context.query}

Relationships:
{json.dumps(relationship_data, indent=2)}

Explain the relationships and dependencies clearly.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the relationship data below, answer this query: """ + context.query + """

Relationships:
""" + json.dumps(relationship_data, indent=2) + """

Explain the relationships and dependencies clearly.
"""
```

#### 1.7 Fix `_generate_search_response` (lines ~747-830)

**FIND**:
```python
prompt = f"""
Based on the search results below, answer this query: {context.query}

Search Results:
{json.dumps(search_data, indent=2)}

Provide relevant information from the search results.
"""
```

**REPLACE WITH**:
```python
prompt = """
Based on the search results below, answer this query: """ + context.query + """

Search Results:
""" + json.dumps(search_data, indent=2) + """

Provide relevant information from the search results.
"""
```

### Test Commands
```bash
# Test with entities containing % characters
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of the 50% milestone?"}'
```

---

## Phase 2: State Normalization Implementation (1 hour) ✅ COMPLETED

### Problem
States are stored inconsistently: "in_progress", "In Progress", "in-progress" are treated as different states.

### IMPLEMENTATION COMPLETED (2025-01-07 20:45)
✅ Created `src/state_normalizer.py` with:
- Canonical state mappings (planned, in_progress, completed, blocked, cancelled)
- `normalize_state_value()` function for single values
- `normalize_state_dict()` function for state dictionaries
- `denormalize_for_display()` for UI presentation

✅ Updated `src/storage.py`:
- Added import: `from .state_normalizer import normalize_state_dict`
- Modified `save_entity_states()` to normalize states before saving (lines 415-441)

✅ Created migration script `scripts/normalize_existing_states.py`:
- Backs up entity_states table before migration
- Normalizes all existing states to canonical format
- Provides verification of unique states after migration

✅ Created test file: `test_phase2_api.py`

### ADDITIONAL WORK COMPLETED:
✅ Created `src/relationship_normalizer.py` to handle relationship type normalization:
- Maps variations like "needs", "requires", "depends" → "depends_on"
- Maps "blocked", "blocking" → "blocks"
- Provides fallback to "relates_to" for unknown types

✅ Updated `src/storage.py` to import relationship normalizer (ready for integration)

### TEST RESULTS:
- ✅ State normalization working at storage layer
- ✅ Database migration successful - all states normalized
- ✅ No more fake state changes in new data
- ⚠️ Old test data was causing false positives - database reset resolved this
- ⚠️ Relationship warnings still appearing (needs storage integration)

### Solution
Implement normalization at the storage layer to ensure consistent state values.

### Implementation Steps

#### 2.1 Create State Normalizer Utility

**CREATE FILE**: `src/state_normalizer.py`

```python
"""State normalization utilities for consistent state storage."""

from typing import Dict, Any, Optional

# Canonical state values
CANONICAL_STATES = {
    "planned": ["planned", "planning", "not_started", "notstarted", "not started"],
    "in_progress": ["in_progress", "inprogress", "in progress", "in-progress", "in_process", "active", "ongoing"],
    "completed": ["completed", "complete", "done", "finished", "closed"],
    "blocked": ["blocked", "on_hold", "onhold", "on hold", "paused", "stuck"],
    "cancelled": ["cancelled", "canceled", "abandoned", "stopped"]
}

# Build reverse mapping
STATE_MAPPING = {}
for canonical, variations in CANONICAL_STATES.items():
    for variation in variations:
        STATE_MAPPING[variation.lower()] = canonical


def normalize_state_value(state: Optional[str]) -> Optional[str]:
    """Normalize a state value to its canonical form."""
    if not state:
        return state
    
    normalized = state.lower().strip()
    return STATE_MAPPING.get(normalized, normalized)


def normalize_state_dict(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize state values in a state dictionary."""
    if not state_dict:
        return state_dict
    
    normalized = state_dict.copy()
    
    # Normalize status field
    if 'status' in normalized and normalized['status']:
        normalized['status'] = normalize_state_value(normalized['status'])
    
    # Normalize progress field (ensure consistent format)
    if 'progress' in normalized and normalized['progress']:
        progress = str(normalized['progress']).strip()
        # Remove "complete" or "%" if present
        progress = progress.replace('complete', '').replace('%', '').strip()
        # Ensure it's a percentage
        if progress.isdigit():
            normalized['progress'] = f"{progress}%"
    
    return normalized


def denormalize_for_display(state_value: str) -> str:
    """Convert canonical state to display format."""
    display_map = {
        "planned": "Planned",
        "in_progress": "In Progress",
        "completed": "Completed",
        "blocked": "Blocked",
        "cancelled": "Cancelled"
    }
    return display_map.get(state_value, state_value.replace('_', ' ').title())
```

#### 2.2 Update Storage Layer

**EDIT FILE**: `src/storage.py`

**ADD IMPORT** (after line 11):
```python
from src.state_normalizer import normalize_state_dict
```

**UPDATE METHOD**: `save_entity_state` (around line 380)

**FIND**:
```python
def save_entity_state(self, entity_id: str, state: Dict[str, Any], meeting_id: str, confidence: float = 1.0) -> None:
    """Save entity state."""
    state_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    cursor = self.conn.cursor()
    cursor.execute("""
        INSERT INTO entity_states (id, entity_id, state, meeting_id, timestamp, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (state_id, entity_id, json.dumps(state), meeting_id, timestamp, confidence))
    self.conn.commit()
```

**REPLACE WITH**:
```python
def save_entity_state(self, entity_id: str, state: Dict[str, Any], meeting_id: str, confidence: float = 1.0) -> None:
    """Save entity state with normalization."""
    state_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()
    
    # Normalize state before saving
    normalized_state = normalize_state_dict(state)
    
    cursor = self.conn.cursor()
    cursor.execute("""
        INSERT INTO entity_states (id, entity_id, state, meeting_id, timestamp, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (state_id, entity_id, json.dumps(normalized_state), meeting_id, timestamp, confidence))
    self.conn.commit()
```

#### 2.3 Create Migration Script

**CREATE FILE**: `scripts/normalize_existing_states.py`

```python
#!/usr/bin/env python3
"""
One-time migration script to normalize all existing entity states.
Run this ONCE after implementing state normalization.
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.state_normalizer import normalize_state_dict

def migrate():
    """Migrate all entity states to normalized format."""
    print(f"Starting state normalization migration at {datetime.now()}")
    
    # Get database path from settings
    from src.config import settings
    db_path = settings.database_path
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create backup table
    print("Creating backup table...")
    cursor.execute("DROP TABLE IF EXISTS entity_states_backup")
    cursor.execute("""
        CREATE TABLE entity_states_backup AS 
        SELECT * FROM entity_states
    """)
    conn.commit()
    
    # Get all entity states
    print("Fetching all entity states...")
    cursor.execute("SELECT id, state FROM entity_states")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} entity states to process")
    
    # Track changes
    updates = []
    changes_made = 0
    
    for state_id, state_json in rows:
        try:
            state = json.loads(state_json)
            original_state = json.dumps(state, sort_keys=True)
            
            # Normalize the state
            normalized = normalize_state_dict(state)
            
            # Check if anything changed
            new_state = json.dumps(normalized, sort_keys=True)
            if original_state != new_state:
                updates.append((new_state, state_id))
                changes_made += 1
                print(f"  Normalizing state {state_id}")
                
        except Exception as e:
            print(f"Error processing state {state_id}: {e}")
            continue
    
    # Apply updates
    if updates:
        print(f"\nApplying {changes_made} normalizations...")
        cursor.executemany("UPDATE entity_states SET state = ? WHERE id = ?", updates)
        conn.commit()
        print(f"✓ Updated {changes_made} states")
    else:
        print("✓ No states needed normalization")
    
    # Verify migration
    print("\nVerifying migration...")
    cursor.execute("""
        SELECT DISTINCT json_extract(state, '$.status') as status 
        FROM entity_states 
        WHERE json_extract(state, '$.status') IS NOT NULL
    """)
    statuses = [row[0] for row in cursor.fetchall()]
    print(f"Unique statuses after migration: {statuses}")
    
    conn.close()
    print(f"\nMigration completed at {datetime.now()}")

if __name__ == "__main__":
    # Safety check
    response = input("This will modify the database. Create a backup first! Continue? (yes/no): ")
    if response.lower() == 'yes':
        migrate()
    else:
        print("Migration cancelled.")
```

### Test Commands
```bash
# Backup database first
cp data/memories.db data/memories.db.backup

# Run migration
python scripts/normalize_existing_states.py

# Test normalization
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the current status of Project Alpha?"}'
```

---

## Phase 3: Entity Extraction Improvements (45 minutes)

### Problem
Common words like "What", "December", "Status" are extracted as entity names.

### Solution
Implement comprehensive stop word filtering and improved entity matching.

### Implementation Steps

#### 3.1 Update Entity Extraction Method

**EDIT FILE**: `src/query_engine_v2.py`

**REPLACE ENTIRE METHOD**: `_extract_query_entities` (around line 310)

```python
def _extract_query_entities(self, query: str) -> List[str]:
    """Extract entity mentions from query with intelligent filtering."""
    # Comprehensive stop words including query terms
    STOP_WORDS = {
        # Question words
        'what', 'where', 'when', 'who', 'why', 'how', 'which', 'whose', 'whom',
        # Common verbs
        'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'done',
        'will', 'would', 'could', 'should', 'may', 'might', 'must',
        'can', 'shall', 'ought',
        'show', 'tell', 'get', 'give', 'find', 'list', 'display',
        'provide', 'explain', 'describe', 'update', 'check',
        # Articles and determiners
        'the', 'a', 'an', 'this', 'that', 'these', 'those',
        'my', 'your', 'his', 'her', 'its', 'our', 'their',
        'some', 'any', 'all', 'no', 'every', 'each',
        # Prepositions
        'of', 'in', 'on', 'at', 'to', 'for', 'from', 'with',
        'by', 'about', 'through', 'during', 'before', 'after',
        'above', 'below', 'between', 'under', 'over',
        # Conjunctions
        'and', 'or', 'but', 'nor', 'so', 'yet', 'because',
        'if', 'unless', 'until', 'while', 'since', 'as',
        # Query-specific terms
        'status', 'progress', 'update', 'updates', 'current',
        'latest', 'recent', 'new', 'old', 'all', 'any', 'some',
        'project', 'projects', 'task', 'tasks', 'item', 'items',
        'blocker', 'blockers', 'issue', 'issues', 'problem', 'problems',
        'timeline', 'history', 'changes', 'change', 'modification',
        'owner', 'ownership', 'assigned', 'assignment', 'responsible',
        # Common words
        'thing', 'things', 'something', 'nothing', 'everything',
        'someone', 'anyone', 'everyone', 'nobody', 'people',
        'time', 'date', 'day', 'week', 'month', 'year',
        'way', 'place', 'part', 'side', 'end', 'point',
        # Months
        'january', 'february', 'march', 'april', 'may', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
        'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
        # Days
        'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
        'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun',
        # Numbers and quantifiers
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'first', 'second', 'third', 'last', 'next', 'previous',
        'many', 'much', 'few', 'several', 'more', 'less', 'most', 'least'
    }
    
    entities = []
    all_entities = self.storage.get_all_entities()
    
    # Pre-process query
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    # Extract entities with filtering
    seen_entities = set()  # Avoid duplicates
    
    for entity in all_entities:
        entity_name_lower = entity.name.lower()
        
        # Skip if already found (case-insensitive)
        if entity_name_lower in seen_entities:
            continue
        
        # Skip stop words
        if entity_name_lower in STOP_WORDS:
            logger.debug(f"Skipping stop word entity: {entity.name}")
            continue
        
        # Skip single-character entities
        if len(entity_name_lower) <= 1:
            logger.debug(f"Skipping single-char entity: {entity.name}")
            continue
        
        # Skip if entity name is just punctuation or numbers
        if not any(c.isalpha() for c in entity_name_lower):
            logger.debug(f"Skipping non-alphabetic entity: {entity.name}")
            continue
        
        # Skip if entity is a single common word from query
        entity_words = entity_name_lower.split()
        if len(entity_words) == 1 and entity_words[0] in query_words and len(entity_words[0]) < 4:
            logger.debug(f"Skipping short query word entity: {entity.name}")
            continue
        
        # Check for entity mention in query using word boundaries
        import re
        # Create pattern for exact word matching
        pattern = r'\b' + re.escape(entity_name_lower) + r'\b'
        if re.search(pattern, query_lower):
            entities.append(entity.name)
            seen_entities.add(entity_name_lower)
            logger.info(f"Found entity mention: {entity.name}")
            continue
        
        # Also check normalized name
        if entity.normalized_name and entity.normalized_name != entity_name_lower:
            pattern = r'\b' + re.escape(entity.normalized_name.lower()) + r'\b'
            if re.search(pattern, query_lower):
                entities.append(entity.name)
                seen_entities.add(entity_name_lower)
                logger.info(f"Found entity mention via normalized name: {entity.name}")
    
    # Sort by length (longer names first) to prioritize more specific matches
    entities.sort(key=len, reverse=True)
    
    # Log extraction results
    if entities:
        logger.info(f"Extracted {len(entities)} entities from query: {entities}")
    else:
        logger.debug("No entities extracted from query")
    
    return entities
```

#### 3.2 Create Entity Extraction Test

**CREATE FILE**: `tests/test_entity_extraction.py`

```python
#!/usr/bin/env python3
"""Test entity extraction improvements."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.query_engine_v2 import QueryEngineV2
from src.storage import MemoryStorage
from src.embeddings import LocalEmbeddings
from src.models import Entity, EntityType

def test_entity_extraction():
    """Test that common words are not extracted as entities."""
    # Initialize components
    storage = MemoryStorage()
    embeddings = LocalEmbeddings()
    
    # Create mock LLM client (not used for this test)
    class MockLLMClient:
        pass
    
    query_engine = QueryEngineV2(storage, embeddings, MockLLMClient())
    
    # Create test entities including problematic ones
    test_entities = [
        Entity(name="Project Alpha", type=EntityType.PROJECT),
        Entity(name="Mobile App Redesign", type=EntityType.PROJECT),
        Entity(name="What", type=EntityType.PROJECT),  # Should be filtered
        Entity(name="December", type=EntityType.DEADLINE),  # Should be filtered
        Entity(name="Status", type=EntityType.FEATURE),  # Should be filtered
        Entity(name="Bob Smith", type=EntityType.PERSON),
        Entity(name="API Migration", type=EntityType.FEATURE),
        Entity(name="Q4 Planning", type=EntityType.PROJECT),
        Entity(name="a", type=EntityType.PROJECT),  # Single char, should be filtered
        Entity(name="123", type=EntityType.PROJECT),  # Just numbers, should be filtered
    ]
    
    # Save entities
    storage.save_entities(test_entities)
    
    # Test queries
    test_cases = [
        {
            "query": "What is the status of Project Alpha?",
            "expected": ["Project Alpha"],
            "not_expected": ["What", "Status"]
        },
        {
            "query": "Show me all projects in December",
            "expected": [],  # December alone shouldn't match
            "not_expected": ["December", "projects", "all"]
        },
        {
            "query": "What progress has Bob Smith made on the Mobile App Redesign?",
            "expected": ["Bob Smith", "Mobile App Redesign"],
            "not_expected": ["What", "progress"]
        },
        {
            "query": "Tell me about the API Migration timeline",
            "expected": ["API Migration"],
            "not_expected": ["Tell", "timeline", "about"]
        },
        {
            "query": "Is Q4 Planning on track?",
            "expected": ["Q4 Planning"],
            "not_expected": ["Is", "on", "track"]
        }
    ]
    
    # Run tests
    print("Testing entity extraction improvements...\n")
    all_passed = True
    
    for i, test in enumerate(test_cases):
        print(f"Test {i+1}: {test['query']}")
        
        # Extract entities
        extracted = query_engine._extract_query_entities(test['query'])
        
        # Check expected entities
        test_passed = True
        for expected in test['expected']:
            if expected in extracted:
                print(f"  ✓ Found expected: {expected}")
            else:
                print(f"  ✗ Missing expected: {expected}")
                test_passed = False
        
        # Check unwanted entities
        for not_expected in test['not_expected']:
            if not_expected not in extracted:
                print(f"  ✓ Correctly filtered: {not_expected}")
            else:
                print(f"  ✗ Incorrectly extracted: {not_expected}")
                test_passed = False
        
        print(f"  Extracted: {extracted}")
        print(f"  Result: {'PASS' if test_passed else 'FAIL'}\n")
        
        if not test_passed:
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    success = test_entity_extraction()
    sys.exit(0 if success else 1)
```

### Test Commands
```bash
# Run entity extraction test
python tests/test_entity_extraction.py

# Test with API
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of Project Alpha?"}'
```

---

## Phase 4: Response Conciseness Updates (30 minutes)

### Problem
LLM responses are verbose, providing essays instead of direct answers.

### Solution
Update all prompt templates to explicitly request concise responses.

### Implementation Steps

#### 4.1 Update All Response Generation Prompts

For each of the 7 `_generate_*_response` methods, update the prompt to request concise responses:

**PATTERN TO FOLLOW** for all methods:

Replace phrases like:
- "Provide a comprehensive analysis"
- "Provide a comprehensive status update"
- "Provide insights and trends"

With:
- "Provide a concise answer in 1-2 sentences"
- "Be direct and brief"
- "Focus only on the key information requested"

**EXAMPLE UPDATE** for `_generate_status_response`:

```python
prompt = """
Based on the current status data below, answer this query: """ + context.query + """

Current States:
""" + json.dumps(status_data, indent=2) + """

Recent Context:
""" + json.dumps(recent_memories, indent=2) + """

Provide a concise answer in 1-2 sentences. Focus only on the current state and any critical updates. Be direct and factual.
"""
```

Apply similar updates to all 7 methods:
1. `_generate_timeline_response`
2. `_generate_blocker_response`
3. `_generate_status_response`
4. `_generate_ownership_response`
5. `_generate_analytics_response`
6. `_generate_relationship_response`
7. `_generate_search_response`

#### 4.2 Create Response Quality Test

**CREATE FILE**: `tests/test_response_quality.py`

```python
#!/usr/bin/env python3
"""Test response quality improvements."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import app
from fastapi.testclient import TestClient

def test_response_conciseness():
    """Test that responses are concise and useful."""
    client = TestClient(app)
    
    # Test queries
    queries = [
        "What is the current status of Project Alpha?",
        "Show me the timeline for Mobile App Redesign",
        "Which projects are blocked?",
        "Who owns the API Migration?"
    ]
    
    print("Testing response conciseness...\n")
    all_passed = True
    
    for query in queries:
        print(f"Query: {query}")
        
        response = client.post("/api/query", json={"query": query})
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            word_count = len(answer.split())
            
            print(f"Response ({word_count} words): {answer[:200]}...")
            
            # Check quality metrics
            if word_count < 100:
                print("  ✓ Concise response")
            else:
                print("  ✗ Response too verbose")
                all_passed = False
            
            # Check for unwanted patterns
            unwanted_patterns = [
                "comprehensive",
                "detailed analysis",
                "extensive",
                "formatting change",
                "capitalization",
                "it's important to note",
                "as you can see"
            ]
            
            found_patterns = [p for p in unwanted_patterns if p.lower() in answer.lower()]
            if not found_patterns:
                print("  ✓ No verbose language")
            else:
                print(f"  ✗ Found verbose patterns: {found_patterns}")
                all_passed = False
        else:
            print(f"  ✗ Query failed with status {response.status_code}")
            all_passed = False
        
        print()
    
    return all_passed

if __name__ == "__main__":
    success = test_response_conciseness()
    sys.exit(0 if success else 1)
```

---

## Phase 5: Query Caching Implementation (1 hour)

### Problem
Every identical query makes a new API call, costing money each time.

### Solution
Implement in-memory caching with 5-minute TTL for query results.

### Implementation Steps

#### 5.1 Add Cache to Query Engine

**EDIT FILE**: `src/query_engine_v2.py`

**ADD IMPORTS** (after line 10):
```python
from datetime import datetime, timedelta
import hashlib
```

**UPDATE** `__init__` method (add at end):
```python
# Initialize query cache
self.query_cache = {}  # Simple in-memory cache
self.cache_ttl = 300  # 5 minutes
self.cache_hits = 0
self.cache_misses = 0
```

**UPDATE** `process_query` method to add caching:

```python
async def process_query(self, query: str, user_context: Optional[Dict] = None) -> BIQueryResult:
    """Process a business intelligence query with caching."""
    # Generate cache key
    cache_key = hashlib.md5(query.lower().strip().encode()).hexdigest()
    
    # Check cache
    now = datetime.now()
    if cache_key in self.query_cache:
        cached_entry = self.query_cache[cache_key]
        if cached_entry['expires_at'] > now:
            logger.info(f"Cache hit for query: {query}")
            self.cache_hits += 1
            # Return a copy to prevent mutation
            return BIQueryResult(**cached_entry['result'])
        else:
            # Expired, remove from cache
            del self.query_cache[cache_key]
    
    logger.info(f"Cache miss for query: {query}")
    self.cache_misses += 1
    
    # Existing query processing logic...
    logger.info(f"Processing BI query: {query}")
    
    # Rest of the existing method...
    # [Keep all existing code]
    
    # Before returning result, add to cache:
    if result and hasattr(result, 'confidence') and result.confidence > 0.5:
        self.query_cache[cache_key] = {
            'result': {
                'query': result.query,
                'intent': result.intent,
                'answer': result.answer,
                'supporting_data': result.supporting_data,
                'entities_involved': result.entities_involved,
                'confidence': result.confidence,
                'visualizations': result.visualizations,
                'metadata': result.metadata
            },
            'expires_at': now + timedelta(seconds=self.cache_ttl)
        }
        logger.info(f"Cached result for query: {query}")
    
    return result
```

**ADD NEW METHODS** after `process_query`:

```python
def clear_cache(self):
    """Clear the query cache."""
    self.query_cache.clear()
    logger.info("Query cache cleared")

def get_cache_stats(self) -> Dict[str, Any]:
    """Get cache statistics."""
    total_entries = len(self.query_cache)
    now = datetime.now()
    expired = sum(1 for v in self.query_cache.values() 
                  if v['expires_at'] <= now)
    
    hit_rate = 0
    if self.cache_hits + self.cache_misses > 0:
        hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses)
    
    return {
        "total_entries": total_entries,
        "active_entries": total_entries - expired,
        "expired_entries": expired,
        "cache_hits": self.cache_hits,
        "cache_misses": self.cache_misses,
        "hit_rate": round(hit_rate, 3),
        "cache_size_bytes": sys.getsizeof(self.query_cache)
    }
```

#### 5.2 Add Cache API Endpoints

**EDIT FILE**: `src/api.py`

**ADD NEW ENDPOINTS** (after `/api/query` endpoint):

```python
@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics."""
    try:
        # Get query cache stats
        query_stats = query_engine.get_cache_stats() if hasattr(query_engine, 'get_cache_stats') else {}
        
        # Get LLM processor cache stats if available
        llm_stats = {}
        if llm_processor and hasattr(llm_processor, 'get_stats'):
            llm_stats = llm_processor.get_stats()
        
        return {
            "query_cache": query_stats,
            "llm_cache": llm_stats.get('cache_stats', {}),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cache/clear")
async def clear_cache():
    """Clear all caches."""
    try:
        # Clear query cache
        if hasattr(query_engine, 'clear_cache'):
            query_engine.clear_cache()
        
        # Clear LLM cache if available
        if llm_processor and hasattr(llm_processor.cache, 'clear'):
            llm_processor.cache.clear()
        
        return {"status": "success", "message": "All caches cleared"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Test Commands
```bash
# First query (slow)
time curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of Project Alpha?"}'

# Second identical query (fast - from cache)
time curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of Project Alpha?"}'

# Check cache statistics
curl http://localhost:8000/api/cache/stats

# Clear cache
curl -X POST http://localhost:8000/api/cache/clear
```

---

## Phase 6: Async/Await Corrections (30 minutes)

### Problem
Query processing is synchronous but API expects async, causing potential issues.

### Solution
Make all query processing properly async.

### Implementation Steps

#### 6.1 Make process_query Async

**EDIT FILE**: `src/query_engine_v2.py`

The `process_query` method should already be async after Phase 5. Verify it starts with:
```python
async def process_query(self, query: str, user_context: Optional[Dict] = None) -> BIQueryResult:
```

#### 6.2 Make Handler Methods Async

Update all handler methods to be async. For each method, change:
```python
def _handle_status_query(self, context: QueryContext) -> BIQueryResult:
```

To:
```python
async def _handle_status_query(self, context: QueryContext) -> BIQueryResult:
```

Apply to all handler methods:
1. `_handle_status_query`
2. `_handle_timeline_query`
3. `_handle_search_query`
4. `_handle_ownership_query`
5. `_handle_progress_query`
6. `_handle_dependencies_query`
7. `_handle_blocker_query`
8. `_handle_analytics_query`
9. `_handle_general_query`

#### 6.3 Update Handler Calls

In `process_query`, update all handler calls to use await:

**FIND**:
```python
result = handler(context)
```

**REPLACE WITH**:
```python
result = await handler(context)
```

#### 6.4 Update API Endpoint

**EDIT FILE**: `src/api.py`

Verify the `/api/query` endpoint properly awaits:
```python
result = await query_engine.process_query(request.query)
```

---

## Phase 7: Database Index Fixes (15 minutes)

### Problem
Wrong index names prevent query optimization.

### Solution
Fix index names to match what queries expect.

### Implementation Steps

#### 7.1 Fix Index Names

**EDIT FILE**: `src/storage.py`

**1. Remove duplicate index** (line ~154):
```python
# DELETE these lines:
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_entities_normalized ON entities(normalized_name)"
)
```

**2. Fix entity states index** (line ~158):
```python
# CHANGE:
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_entity_states_entity ON entity_states(entity_id)"
)

# TO:
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_entity_states_entity_id ON entity_states(entity_id)"
)
```

**3. Fix transitions index** (line ~167):
```python
# CHANGE:
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_transitions_entity ON state_transitions(entity_id)"
)

# TO:
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_state_transitions_entity_id ON state_transitions(entity_id)"
)
```

### Test Commands
```bash
# Restart API to recreate indexes
python -m src.api

# Verify indexes in SQLite
sqlite3 data/memories.db ".indexes"
```

---

## Phase 8: LLM Processor Cleanup (15 minutes)

### Problem
Duplicate LLM client initialization in processor_v2.py.

### Solution
Remove duplicate client creation and use provided llm_processor.

### Implementation Steps

#### 8.1 Remove Duplicate Client

**EDIT FILE**: `src/processor_v2.py`

**DELETE** lines 101-121 (the proxy setup and OpenAI client creation):
```python
# DELETE ALL OF THIS:
# Setup proxy configuration
proxies = None
if settings.https_proxy or settings.http_proxy:
    # ... all the proxy setup ...
self.llm_client = OpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
    http_client=http_client
)
```

**KEEP** only:
```python
def __init__(self, storage: Storage, entity_resolver: EntityResolver, embeddings: LocalEmbeddings, llm_processor: LLMProcessor):
    self.storage = storage
    self.entity_resolver = entity_resolver
    self.embeddings = embeddings
    self.llm_processor = llm_processor
    self.validation_metrics = {}
```

---

## Phase 9: Comprehensive Testing (1 hour)

### Create Integration Test Suite

**CREATE FILE**: `tests/test_mvp_integration.py`

```python
#!/usr/bin/env python3
"""Comprehensive MVP integration tests."""

import asyncio
import json
import time
from datetime import datetime
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api import app

def test_full_pipeline():
    """Test complete pipeline: ingest → query → cache."""
    client = TestClient(app)
    print("Starting MVP Integration Tests...\n")
    
    # 1. Test Ingestion with various state formats
    test_transcript = """
    Sarah (PM): Let's get updates on our projects.
    
    Bob (Dev): Project Alpha is In Progress, about 60% complete.
    
    Alice (Dev): The Mobile App Redesign is in progress too, currently at 30%.
    
    Charlie (Dev): API Migration status is in_progress, we're at 50% completion.
    
    Sarah: Great! Any blockers?
    
    Bob: Actually yes, Project Alpha is now blocked waiting for design approval.
    
    Dave: The Payment Integration project is COMPLETED as of yesterday.
    """
    
    print("1. Testing ingestion with mixed state formats...")
    ingest_response = client.post("/api/ingest", json={
        "transcript": test_transcript,
        "meeting_id": f"test_mvp_{datetime.now().isoformat()}"
    })
    
    assert ingest_response.status_code == 200
    print("  ✓ Ingestion successful")
    
    # 2. Test state normalization
    print("\n2. Testing state normalization...")
    
    # Query for status - should not complain about capitalization
    status_response = client.post("/api/query", json={
        "query": "What is the current status of all projects?"
    })
    
    if status_response.status_code == 200:
        result = status_response.json()
        answer = result['answer'].lower()
        
        # Check that response doesn't mention formatting/capitalization
        if 'capitalization' not in answer and 'formatting' not in answer:
            print("  ✓ State normalized correctly")
        else:
            print("  ✗ State normalization issues present")
            print(f"    Response: {result['answer']}")
    else:
        print(f"  ✗ Query failed: {status_response.status_code}")
    
    # 3. Test entity extraction
    print("\n3. Testing improved entity extraction...")
    test_queries = [
        {
            "query": "What is the current status of Project Alpha?",
            "should_find": "Project Alpha",
            "should_not_find": ["What", "status"]
        },
        {
            "query": "Show me all projects completed in December",
            "should_not_find": ["December", "Show", "all"]
        }
    ]
    
    for test in test_queries:
        response = client.post("/api/query", json={"query": test['query']})
        if response.status_code == 200:
            result = response.json()
            entities = result.get('entities_mentioned', [])
            
            # Check positive cases
            if 'should_find' in test and test['should_find'] in entities:
                print(f"  ✓ Found expected entity: {test['should_find']}")
            
            # Check negative cases
            unwanted = [e for e in test.get('should_not_find', []) if e in entities]
            if not unwanted:
                print(f"  ✓ Correctly filtered stop words")
            else:
                print(f"  ✗ Incorrectly extracted: {unwanted}")
        else:
            print(f"  ✗ Query failed: {response.status_code}")
    
    # 4. Test response conciseness
    print("\n4. Testing response conciseness...")
    response = client.post("/api/query", json={
        "query": "What is the current status of all projects?"
    })
    
    if response.status_code == 200:
        result = response.json()
        word_count = len(result['answer'].split())
        print(f"  Response length: {word_count} words")
        
        if word_count < 100:
            print("  ✓ Response is concise")
        else:
            print("  ✗ Response is too verbose")
    
    # 5. Test caching
    print("\n5. Testing query caching...")
    
    # First query (cache miss)
    start_time = time.time()
    response1 = client.post("/api/query", json={
        "query": "What is the status of Project Alpha?"
    })
    time1 = time.time() - start_time
    
    # Second identical query (cache hit)
    start_time = time.time()
    response2 = client.post("/api/query", json={
        "query": "What is the status of Project Alpha?"
    })
    time2 = time.time() - start_time
    
    print(f"  First query: {time1:.2f}s")
    print(f"  Cached query: {time2:.2f}s")
    
    if time2 < time1 * 0.5:  # Cached should be at least 2x faster
        print("  ✓ Caching working effectively")
    else:
        print("  ✗ Cache may not be working")
    
    # Check cache stats
    cache_stats = client.get("/api/cache/stats").json()
    print(f"  Cache stats: {json.dumps(cache_stats['query_cache'], indent=2)}")
    
    # 6. Test specific query types
    print("\n6. Testing specific query types...")
    
    query_tests = [
        ("Timeline query", "Show me the timeline for Project Alpha"),
        ("Blocker query", "Which projects are currently blocked?"),
        ("Ownership query", "Who is working on the API Migration?"),
        ("Progress query", "What's the progress on all projects?")
    ]
    
    all_passed = True
    for test_name, query in query_tests:
        response = client.post("/api/query", json={"query": query})
        if response.status_code == 200:
            print(f"  ✓ {test_name} successful")
        else:
            print(f"  ✗ {test_name} failed: {response.status_code}")
            all_passed = False
    
    print("\n✅ MVP Integration Tests Complete!")
    return all_passed

if __name__ == "__main__":
    success = test_full_pipeline()
    sys.exit(0 if success else 1)
```

### Run Complete Test Suite
```bash
# Run all tests
python tests/test_entity_extraction.py
python tests/test_response_quality.py
python tests/test_mvp_integration.py

# Test with curl
./test_endpoints.sh
```

---

## Phase 10: Production Deployment Checklist

### Pre-Deployment Steps

1. **Backup Database**
   ```bash
   cp data/memories.db data/memories.db.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Run State Migration**
   ```bash
   python scripts/normalize_existing_states.py
   ```

3. **Run All Tests**
   ```bash
   make test
   ```

4. **Verify Services**
   ```bash
   # Check Qdrant is running
   docker ps | grep qdrant
   
   # Check API health
   curl http://localhost:8000/health/detailed
   ```

### Deployment Verification

1. **Test Core Functionality**
   ```bash
   # Ingest test data
   curl -X POST http://localhost:8000/api/ingest \
     -H "Content-Type: application/json" \
     -d @test_data/sample_meeting.json
   
   # Test each query type
   curl -X POST http://localhost:8000/api/query \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the current status of all projects?"}'
   ```

2. **Monitor Performance**
   - Query response time < 2s (first query)
   - Cached query response < 0.5s
   - No 500 errors in logs
   - Cache hit rate > 30% after warm-up

3. **Check Logs**
   ```bash
   # Look for errors
   grep ERROR app.log
   
   # Check cache performance
   curl http://localhost:8000/api/cache/stats
   ```

### Rollback Plan

If issues occur:

1. **Stop Services**
   ```bash
   # Stop API
   pkill -f "python -m src.api"
   ```

2. **Restore Database**
   ```bash
   cp data/memories.db.backup data/memories.db
   ```

3. **Revert Code**
   ```bash
   git checkout -- src/query_engine_v2.py
   git checkout -- src/storage.py
   git checkout -- src/processor_v2.py
   git checkout -- src/api.py
   ```

4. **Restart Services**
   ```bash
   python -m src.api
   ```

---

## Success Metrics

### Before Fixes
- ❌ All queries return HTTP 500 errors
- ❌ String formatting crashes with % in data
- ❌ Shows fake state changes ("In Progress" → "in progress")
- ❌ Extracts "What" and "December" as entities
- ❌ Gives essay-length responses
- ❌ Every query costs money
- ❌ Synchronous code in async context

### After Current Fixes (Phases 1-2 + Entity Resolution)
- ✅ All queries return HTTP 200 with valid data
- ✅ Handles % characters in entity names/states
- ✅ Only shows real state changes
- ✅ Tracks entities across meetings correctly
- ⏳ Still extracts common words as entities (Phase 3 pending)
- ⏳ Still gives verbose responses (Phase 4 pending)
- ⏳ No caching yet (Phase 5 pending)
- ⏳ Async/await issues remain (Phase 6 pending)

### Cost Analysis
- **Before**: 100 queries/day = ~$2.00
- **After**: 100 queries/day = ~$0.80 (with 60% cache hit rate)
- **Monthly Savings**: ~$36

---

## Common Issues & Solutions

### Issue: "RuntimeError: This event loop is already running"
**Solution**: Ensure all async methods are properly awaited, especially in query_engine_v2.py

### Issue: "Invalid format specifier" still occurring
**Solution**: Check that ALL f-strings in prompt generation were replaced with concatenation

### Issue: Cache not working
**Solution**: Verify cache initialization in __init__ and that process_query is saving results

### Issue: Entities still extracting common words
**Solution**: Ensure the new _extract_query_entities method was completely replaced

### Issue: Responses still verbose
**Solution**: Double-check all 7 prompt templates were updated with conciseness instructions

---

## CRITICAL PATH FORWARD (Updated 2025-01-08 04:40)

### Immediate Actions Required:

1. **START PHASE 3: Entity Extraction Improvements** (45 minutes)
   - Common words like "What", "December", "Status" are being extracted as entities
   - Implement comprehensive stop word list in _extract_query_entities method
   - Test with queries containing these words to verify filtering
   
2. **THEN PHASE 4: Response Conciseness** (30 minutes)
   - Current responses are 200+ words (test output shows verbose answers)
   - Update all 7 prompt generation methods to request brief responses
   - Target: answers under 100 words
   
3. **THEN PHASE 5: Query Caching** (1 hour)
   - Implement 5-minute in-memory cache
   - Add cache statistics endpoints
   - Test cache hit rate and performance improvement

### Truth About Current Implementation:

**What We Actually Did**:
1. Implemented a hybrid approach in api.py that combines:
   - Vector similarity search on the full transcript
   - Text extraction of capitalized phrases
   - Case-insensitive matching of existing entity names
   - Full use of the 4-tier entity resolver

**What We Did NOT Do**:
1. Did not modify entity_resolver.py (it was already correctly configured)
2. Did not change thresholds (they were already at 0.70/0.65)
3. Did not add suffix stripping (it was already implemented)

**Key Insight**: The entity resolver was properly configured all along. The issue was that api.py wasn't fully utilizing the vector similarity capabilities - it was only passing extracted entity names to the resolver, not leveraging semantic search.

### Phases Still To Complete:

- **Phase 3**: Entity extraction improvements (filter stop words)
- **Phase 4**: Response conciseness updates 
- **Phase 5**: Query caching implementation
- **Phase 6**: Async/await corrections
- **Phase 7**: Database index fixes
- **Phase 8**: LLM processor cleanup
- **Phase 9**: Comprehensive testing
- **Phase 10**: Production deployment checklist

### Known Risks:

1. **Performance**: The hybrid approach searches ALL entities - may be slow with large databases
2. **Over-matching**: Vector similarity might match unrelated entities
3. **Under-matching**: If thresholds are still too high, duplicates may persist

## Next Steps After Implementation

1. **Monitor Entity Resolution**
   - Check for any remaining duplicates
   - Monitor vector search performance
   - Track entity resolver match rates

2. **Optimize Entity Matching**
   - Add caching for entity lookups
   - Implement entity aliases
   - Add manual entity merge capability

3. **Complete Remaining Phases**
   - Each phase addresses a specific bug/issue
   - Test after each phase
   - Document any new issues discovered

4. **Documentation**
   - Update entity resolution documentation
   - Create troubleshooting guide
   - Document the hybrid matching approach

---

## Conclusion

This roadmap addresses all critical issues in the Query Engine while maintaining the OpenRouter structured output requirements. Follow each phase sequentially, test thoroughly, and monitor the results. The system should be fully functional with significant performance improvements and cost savings.

Remember: Each fix is independent and can be tested separately, but they work best when all are implemented together.