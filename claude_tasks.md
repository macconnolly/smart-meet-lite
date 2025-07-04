# Claude Tasks: Smart-Meet Lite Prioritized Implementation Plan

This document contains the prioritized task plans for fixing Smart-Meet Lite's critical issues first, then enhancing functionality, with non-essential items moved to the end.

## Recent Progress Update (2025-07-01)

### ✅ COMPLETED: Entity Embeddings Migration to Qdrant
- Successfully migrated 1046 entity embeddings from SQLite BLOBs to Qdrant
- Achieved **56.3x performance improvement** (135+ seconds → 2.40 seconds average)
- 100% query success rate (previously 0% due to timeouts)
- Created comprehensive migration script with backup
- Updated all affected modules (models, storage, processor, entity_resolver)
- Full details in `migration_report.md`

### ✅ COMPLETED: Removal of Artificial Truncations
- Removed [:5] limits on decisions and action_items in extractor.py
- Removed [:5] and [:10] limits in query_engine.py confidence calculations
- Increased entity description context from 50 to 200 characters
- Made timeline display limit configurable (default: 5, adjustable via settings)
- Created test suite `test_truncation_removal.py`
- Full details in `truncation_removal_summary.md`

### ✅ COMPLETED: Entity Resolution Architecture Fix
- Connected EntityResolver to EntityProcessor (previously separate implementations)
- Fixed false positive matches ("vendor quotes for infrastructure" ≠ "vendor issues")
- Implemented shared resolver with multi-strategy approach (exact, fuzzy, vector, LLM)
- Added configurable thresholds and use_llm flag
- Clean reset performed to eliminate historical bad data
- Full details in `003-Truncation Removal and Entity Resolution Issues.md`

### 🔴 CRITICAL ISSUE DISCOVERED: State Tracking Failures
During testing after entity resolution fix:
- **Only 16 state transitions** created when 100+ expected
- **Timeline queries failing** with 500 errors or empty results
- **Root Cause**: LLM doesn't know prior states, cannot detect changes
- **Impact**: No historical tracking, broken business intelligence features
- Full details in `004-State-Tracking-and-Timeline-Issues-DETAILED.md`

---

## Current Critical Implementation Plan (July 1, 2025)

### Overview of Current Gaps

1. **State Tracking Broken**: Only 16/100+ transitions detected
2. **Missing Metadata**: Email context, project tags, meeting types stripped
3. **Query Classification Failing**: Blocker/timeline queries misclassified
4. **No State Inference**: Implicit state changes not captured
5. **Limited Business Intelligence**: Can't track project evolution

### Phase 1: Enhanced Data Capture & Storage (3 hours)

#### 1.1 Update Database Schema
**File**: `src/storage.py` - `_init_sqlite()` method (line ~46)

Add new columns to capture rich metadata:
```sql
ALTER TABLE meetings ADD COLUMN email_metadata TEXT DEFAULT NULL;
ALTER TABLE meetings ADD COLUMN project_tags TEXT DEFAULT '[]';
ALTER TABLE meetings ADD COLUMN meeting_type TEXT DEFAULT 'unknown';
ALTER TABLE meetings ADD COLUMN actual_start_time TIMESTAMP DEFAULT NULL;
ALTER TABLE meetings ADD COLUMN actual_end_time TIMESTAMP DEFAULT NULL;
ALTER TABLE meetings ADD COLUMN detailed_summary TEXT DEFAULT NULL;
ALTER TABLE meetings ADD COLUMN raw_extraction TEXT DEFAULT NULL;
ALTER TABLE meetings ADD COLUMN organization_context TEXT DEFAULT NULL;
```

#### 1.2 Update Meeting Model
**File**: `src/models.py` - Meeting class (line ~121)

Add corresponding fields to dataclass for new metadata.

#### 1.3 Complete EML Processing Enhancement
**File**: `ingest_eml_files.py` - Replace `parse_eml_file()` function

- Extract and preserve email metadata (From, To, CC, Date, Thread ID)
- Parse organization context from email domains
- Keep email headers for context instead of stripping
- Return structured data with all metadata

#### 1.4 Update Ingestion Script
**File**: `ingest_eml_files.py` - Update `ingest_meeting()` function

Pass all metadata through API ingestion endpoint.

#### 1.5 Update API Request Model
**File**: `src/api.py` - Add IngestRequest model

Include all new metadata fields in API request structure.

### Phase 2: Fix State Tracking with Prior Context (3 hours)

#### 2.1 Add Storage Methods for State History
**File**: `src/storage.py` - Add after line ~440

- `get_all_entity_current_states()` - SQLite-compatible query for all current states
- `get_entity_state_history()` - Full history for timeline building
- `update_meeting_raw_extraction()` - Store extraction for future use

#### 2.2 Update Extractor with Helper Methods
**File**: `src/extractor.py` - Add before `extract_meeting_info()`

- `_infer_meeting_type()` - Classify meeting from email metadata
- `_extract_project_from_title()` - Extract project name from title patterns

#### 2.3 Enhanced Extractor with Prior States
**File**: `src/extractor.py` - Replace `extract_meeting_info()` method

Pass prior states to LLM with enhanced prompt that:
- Shows all entity prior states
- Instructs comparison and change detection
- Captures detailed summary and metadata

#### 2.4 Update API Endpoint
**File**: `src/api.py` - Replace `/api/ingest` endpoint

c

### Phase 3: State Inference from Content (1.5 hours)

#### 3.1 Add State Inference to Processor
**File**: `src/processor.py` - Add `_infer_state_changes_from_content()`

Pattern-based detection for:
- Status changes: "is now in progress", "has been completed", "is blocked"
- Progress updates: "at 75% complete"
- Risk indicators: "at risk", "may slip"

#### 3.2 Integrate State Inference
**File**: `src/processor.py` - Update `process_extraction()`

Combine explicit LLM-detected changes with inferred changes.

### Phase 4: Fix Query Intent Classification (1 hour)

#### 4.1 Enhanced Intent Detection
**File**: `src/query_engine.py` - Replace `parse_intent()` method

Comprehensive pattern matching with scoring system for:
- Timeline queries
- Blocker queries
- Status queries
- Ownership queries

#### 4.2 Timeline Query Fallback
**File**: `src/query_engine.py` - Update `_answer_timeline_query()`

If no transitions exist, reconstruct from state history.

### Phase 5: Comprehensive Test Suite (1 hour)

#### 5.1 State Transition Test
**File**: `test_state_transitions.py`

Test explicit transitions, inferred changes, blocker detection, progress tracking.

---

## Task Priority List

### 🔴 CRITICAL - Immediate (Today)

1. **Enhanced Data Capture** (Phase 1)
   - Update database schema for metadata
   - Fix EML processing to preserve context
   - Capture project tags and meeting types

2. **Fix State Tracking** (Phase 2)
   - Pass prior states to LLM
   - Enable change detection
   - Store raw extractions

3. **State Inference** (Phase 3)
   - Pattern-based state detection
   - Capture implicit changes

### 🟡 ESSENTIAL - Tomorrow

4. **Query Classification** (Phase 4)
   - Fix intent detection
   - Add timeline fallbacks

5. **Comprehensive Testing** (Phase 5)
   - Verify all fixes work together
   - Test edge cases

### 🟢 IMPORTANT - This Week

6. **Data Migration**
   - Migrate historical data with new extraction
   - Backfill missing state transitions

7. **Advanced Analytics**
   - Project burndown tracking
   - Team velocity metrics
   - Blocker analysis

### ⚪ NON-ESSENTIAL - Next Week

8. **Security Hardening**
   - Remove SSL bypass
   - Proper CORS configuration

9. **Monitoring & Optimization**
   - Performance metrics
   - Query optimization
   - Cache tuning

---

## Expected Outcomes

After implementing these fixes:

1. **State Transitions**: 16 → 100+ per test suite
2. **Timeline Queries**: 500 errors → Full historical data
3. **Blocker Queries**: 0.20 → 0.80+ confidence
4. **Data Richness**: 10x more metadata captured
5. **Business Intelligence**: True project tracking enabled

---

## Implementation Notes

- Each phase builds on the previous
- Test after each phase to verify
- Keep backward compatibility
- Document all schema changes

The system will transform from a basic meeting search tool into a true business intelligence platform that tracks organizational knowledge evolution over time.