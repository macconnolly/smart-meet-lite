# LLM Orientation Prompt for Smart-Meet-Lite

## YOUR MISSION
Fix a broken meeting intelligence system. The system WAS WORKING before complex state tracking was added. Your job: make it work again by following EXACT fixes listed below. DO NOT add features. DO NOT refactor. Just fix what's broken.

## WHAT THIS SYSTEM DOES
1. **Ingests** meeting transcripts
2. **Extracts** entities (people, projects, features) and their states
3. **Stores** in dual database (SQLite for structured data, Qdrant for vector search)
4. **Searches** using both semantic similarity and business logic
5. **Tracks** how entities change over time

## CURRENT STATUS
- ✅ All components exist
- ❌ They're not properly connected
- ❌ Database indexes have wrong names
- ❌ Regex patterns break state tracking
- ❌ Query engine isn't async
- ❌ Missing self-healing validation

## START HERE - READ THESE FILES IN ORDER

1. **`claude_tasks.md`** - Your step-by-step fix guide with EXACT line numbers
2. **`014_Hyper_Detailed_Current_State_Analysis.md`** - Forensic analysis of what's broken
3. **`src/storage.py`** - Lines 154-172 need index fixes
4. **`src/processor_v2.py`** - Lines 31-312 need major cleanup
5. **`src/query_engine_v2.py`** - Line 147 needs async

## QUICKSTART COMMANDS

```bash
# 1. Check what's modified
git status

# 2. Start Qdrant (REQUIRED - vector database)
docker-compose up -d

# 3. Start API
python -m src.api

# 4. Test it works
curl http://localhost:8000/health/detailed
```

## THE 7 FIXES YOU MUST MAKE

### Fix 1: Database Indexes (storage.py)
- DELETE duplicate index at line 154-156
- RENAME index at line 158: `idx_entity_states_entity` → `idx_entity_states_entity_id`
- RENAME index at line 167: `idx_transitions_entity` → `idx_state_transitions_entity_id`

### Fix 2: Remove Regex (processor_v2.py)
- DELETE lines 31-93 (all pattern definitions)
- DELETE lines 101-121 (duplicate LLM client)
- DELETE methods: `_infer_states_from_patterns`, `_extract_progress_indicators`, `_extract_assignments`
- DELETE `_merge_state_information` method

### Fix 3: Simplify Processing (processor_v2.py)
- REPLACE lines 150-164 in `process_meeting_with_context` with simpler flow
- Just extract states and create transitions, no pattern matching

### Fix 4: Use Batch Operations (processor_v2.py)
- Line 641: Change `save_entities` → `save_entities_batch`

### Fix 5: Make Query Async (query_engine_v2.py)
- Line 147: Add `async` to `process_query` method

### Fix 6: Add Entity Resolver (processor_v2.py)
- Line ~606: Add entity resolver usage before direct lookup

### Fix 7: Add Self-Healing (processor_v2.py)
- ADD `_validate_state_tracking_completeness` method after line 543
- CALL it in `process_meeting_with_context`

## HOW TO TEST YOUR FIXES

```bash
# Test 1: Ingest a meeting
curl -X POST http://localhost:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Meeting",
    "transcript": "Alice said the API is in progress. Bob owns the database."
  }'

# Test 2: Search for content
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "API progress", "limit": 5}'

# Test 3: Business query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of all projects?"}'
```

## SUCCESS LOOKS LIKE
1. API starts without errors
2. `/health/detailed` shows all green
3. Ingestion creates entities and state transitions (check logs)
4. Search returns relevant memories
5. Queries return structured data about entities

## COMMON PITFALLS
- Don't create new files
- Don't add import statements (all needed imports exist)
- Don't change working code (only fix what's listed)
- Don't optimize or refactor
- Test after EACH fix, not all at once

## WHERE TO FIND HELP
- `CLAUDE.md` - Project overview
- `010_Master_Implementation_Plan.md` - Original requirements
- Error logs: Check terminal where API is running
- Database: `smart_meet.db` (SQLite browser helpful)

## YOUR FIRST COMMAND
```bash
cd /path/to/smart-meet-lite
cat claude_tasks.md | head -100
```

This will show you the exact fixes to make. Follow them precisely. The system was working before - we just need to reconnect the pieces properly.

Remember: You're a surgeon, not an architect. Make precise cuts, not redesigns.