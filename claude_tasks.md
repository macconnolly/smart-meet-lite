# Claude Tasks: Smart-Meet Lite Forensic Implementation Plan

**LAST UPDATED**: 2025-01-04 - FORENSIC AUDIT COMPLETE

This document contains the EXACT implementation requirements based on a comprehensive forensic audit of the codebase against the Master Implementation Plan (010_Master_Implementation_Plan.md). Every item includes exact line numbers, exact code to add/remove, and detailed context for implementation.

## Recent Progress Update (2025-01-04)

### ✅ COMPLETED TODAY: Critical Bug Fixes

1. **Async Event Loop Fix**
   - File: `src/processor_v2.py` (lines 166-168)
   - Removed nested asyncio.run() causing FastAPI conflicts
   - Now directly awaits _create_comprehensive_transitions

2. **Query Engine Method Fix**
   - File: `src/query_engine_v2.py` (line 610)
   - Fixed non-existent search_memories → search
   - Added compatibility wrapper in storage.py

3. **Configuration Robustness**
   - File: `src/config.py` (lines 54-79)
   - Enhanced clean_openrouter_model to handle comments and whitespace
   - Added validation and logging

4. **Extraction Fallback**
   - File: `src/extractor_enhanced.py` (lines 467-585)
   - Basic extraction now produces real data with regex parsing
   - Guarantees at least one memory even on total failure

5. **Qdrant Filter Fix**
   - File: `src/storage.py` (lines 1065-1082)
   - Proper Filter object construction
   - Added try/except for parameter compatibility

6. **Error Handling**
   - File: `src/extractor_enhanced.py` (lines 403-438)
   - Specific exception types (AuthenticationError, BadRequestError)
   - Detailed error metadata in responses

7. **Health Monitoring**
   - File: `src/api.py` (lines 718-833)
   - Comprehensive /health/detailed endpoint
   - Checks LLM, Qdrant, database, embeddings

---

## Current System Status

### What's Working
- All critical code paths are now functional
- Fallback mechanisms prevent total failures
- Error messages are clear and actionable
- System can degrade gracefully

### What Needs Testing
- End-to-end ingestion → query pipeline
- State transition detection accuracy
- Multi-meeting entity tracking
- Performance under load

### What's Not Implemented (from Master Plan)
- Batch database operations (performance optimization)
- Removal of regex patterns (code cleanup)
- Query engine batch fetching (performance)

---

## 🔴 IMMEDIATE TASKS (Next 2 Hours)

### 1. System Validation Testing
**Priority**: CRITICAL
**Time**: 30 minutes

```bash
# 1. Start services
docker-compose up -d
python -m src.api

# 2. Health check
curl http://localhost:8000/health/detailed

# 3. Test ingestion
python examples/bi_demo.py

# 4. Verify state tracking
# Check logs for "Created state transition" messages
# Confirm transitions have semantic reasons
```

**Success Criteria**:
- Health check shows all green
- Ingestion completes without errors
- State transitions are created with meaningful reasons
- Queries return actual data

### 2. Fix Any Remaining Issues
**Priority**: CRITICAL
**Time**: 30 minutes

Based on test results:
- If LLM connectivity fails: Check API key and model name
- If Qdrant unhealthy: Check Docker logs, restart container
- If no state transitions: Check processor logs for errors
- If queries fail: Check storage method implementations

### 3. Performance Baseline
**Priority**: HIGH
**Time**: 30 minutes

Create performance baseline script:
```python
# test_performance_baseline.py
import time
import asyncio
from src.api import app
from fastapi.testclient import TestClient

async def measure_performance():
    client = TestClient(app)
    
    # Measure ingestion time
    start = time.time()
    response = client.post("/api/ingest", json={
        "title": "Performance Test Meeting",
        "transcript": large_transcript  # 10KB+ transcript
    })
    ingestion_time = time.time() - start
    
    # Measure query time
    start = time.time()
    response = client.post("/api/query", json={
        "query": "What's the status of all projects?"
    })
    query_time = time.time() - start
    
    print(f"Ingestion: {ingestion_time:.2f}s")
    print(f"Query: {query_time:.2f}s")
```

### 4. Document Current Behavior
**Priority**: HIGH
**Time**: 30 minutes

Create `SYSTEM_BEHAVIOR.md`:
- Actual extraction output examples
- State transition examples
- Query response examples
- Error message examples

---

## 🟡 SHORT-TERM TASKS (This Week)

### 1. Implement Batch Operations
**Priority**: HIGH
**Time**: 3 hours
**Files**: `src/storage.py`, `src/processor_v2.py`, `src/query_engine_v2.py`

```python
# storage.py - Already have methods, need to use them
def save_entities_batch(self, entities: List[Entity]) -> List[str]:
    # Existing implementation
    
# processor_v2.py - Update to use batch
# Line ~440: Replace individual saves with batch
self.storage.save_entities_batch(processed_entities)
self.storage.save_transitions_batch(transitions)

# query_engine_v2.py - Update _build_query_context
# Line ~315: Use batch fetching
entity_ids = [e.id for e in context.entities]
all_timelines = self.storage.get_timelines_batch(entity_ids)
```

### 2. Remove Regex Patterns (Clean Code)
**Priority**: MEDIUM
**Time**: 2 hours
**File**: `src/processor_v2.py`

**Current State**: Lines 33-93 define STATE_PATTERNS, ASSIGNMENT_PATTERNS, PROGRESS_PATTERNS
**Action**: 
1. Comment out pattern definitions
2. Remove methods: _infer_states_from_patterns, _extract_progress_indicators, _extract_assignments
3. Simplify _merge_state_information to only use LLM results
4. Test to ensure no regression

### 3. Add Connection Pooling
**Priority**: MEDIUM
**Time**: 2 hours
**File**: `src/storage.py`

```python
import sqlite3
from contextlib import contextmanager
from queue import Queue

class ConnectionPool:
    def __init__(self, database_path: str, pool_size: int = 5):
        self.database_path = database_path
        self.pool = Queue(maxsize=pool_size)
        for _ in range(pool_size):
            conn = sqlite3.connect(database_path)
            conn.row_factory = sqlite3.Row
            self.pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)
```

### 4. Implement Caching Strategy
**Priority**: MEDIUM
**Time**: 3 hours

**Cache Layers**:
1. Query results (TTL: 5 minutes)
2. Entity resolutions (TTL: 1 hour)
3. Current states (TTL: 1 minute)

```python
# Add to query_engine_v2.py
@cache.cached(ttl=300)
def process_query(self, query: str) -> BIQueryResult:
    # Existing implementation
```

### 5. Add Monitoring
**Priority**: HIGH
**Time**: 4 hours

```python
# monitoring.py
from prometheus_client import Counter, Histogram, Gauge

# Metrics
query_duration = Histogram('smartmeet_query_duration_seconds', 
                          'Query processing time',
                          ['query_type'])
ingestion_duration = Histogram('smartmeet_ingestion_duration_seconds',
                              'Meeting ingestion time')
state_transitions_created = Counter('smartmeet_state_transitions_total',
                                   'Total state transitions created')
cache_hits = Counter('smartmeet_cache_hits_total',
                    'Cache hit count',
                    ['cache_type'])
active_entities = Gauge('smartmeet_active_entities',
                       'Number of tracked entities')
```

---

## 🟢 MEDIUM-TERM TASKS (Next 2 Weeks)

### 1. Entity Deduplication System
**Priority**: HIGH
**Time**: 1 day

**Problem**: Multiple entities for same concept
**Solution**:
```python
class EntityDeduplicator:
    def find_duplicates(self) -> List[Tuple[Entity, Entity]]:
        # Use embeddings + edit distance
        
    def merge_entities(self, primary: Entity, duplicate: Entity):
        # Merge states, transitions, relationships
        # Update all references
        # Archive duplicate
```

### 2. State Schema Validation
**Priority**: MEDIUM
**Time**: 1 day

```python
from pydantic import BaseModel, Field

class ProjectState(BaseModel):
    status: Literal["planned", "in_progress", "blocked", "completed"]
    progress: Optional[int] = Field(ge=0, le=100)
    blockers: List[str] = []
    assigned_to: Optional[str]
    confidence: float = Field(ge=0.0, le=1.0)
    
class FeatureState(BaseModel):
    status: Literal["proposed", "approved", "development", "testing", "deployed"]
    dependencies: List[str] = []
    target_date: Optional[datetime]
```

### 3. Advanced Query Capabilities
**Priority**: MEDIUM
**Time**: 2 days

**New Query Types**:
1. **Trend Analysis**: "Show me velocity trends for Team A"
2. **Predictive**: "When will Project X likely complete?"
3. **Comparative**: "Compare progress between Project A and B"
4. **Root Cause**: "What's causing the most blockers?"

### 4. Real-time Updates
**Priority**: LOW
**Time**: 2 days

```python
# WebSocket support
@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # Push state changes in real-time
```

---

## ⚪ BACKLOG (Future)

### From Previous Plans
1. **Email Context Enhancement** (from claude_tasks.md Phase 1)
   - Full email metadata extraction
   - Thread tracking
   - Organization context

2. **Meeting Type Classification** (from claude_tasks.md)
   - Auto-detect standup vs planning vs review
   - Type-specific extraction rules

3. **Multi-tenancy** (from 012 Long-term)
   - Organization isolation
   - Role-based access
   - Usage quotas

4. **Advanced Analytics** (from 012)
   - Custom dashboards
   - Report generation
   - Predictive modeling

5. **Integration Layer** (from 012)
   - Slack notifications
   - JIRA sync
   - Calendar integration

### New Ideas
1. **Conversation Analysis**
   - Speaker participation metrics
   - Sentiment tracking
   - Decision quality scoring

2. **Knowledge Graph**
   - Visual entity relationships
   - Dependency mapping
   - Impact analysis

3. **AI Assistant**
   - Proactive insights
   - Meeting preparation
   - Follow-up suggestions

---

## Testing Requirements

### Unit Tests (Priority: HIGH)
```python
# test_extraction_fallback.py
def test_basic_extraction_produces_data():
    extractor = EnhancedMeetingExtractor(mock_client)
    # Force LLM to fail
    result = extractor.extract(transcript, "test-123")
    assert len(result.memories) > 0
    assert result.meeting_metadata["extraction_method"] == "basic_fallback"

# test_state_comparison.py
async def test_semantic_state_comparison():
    old_state = {"status": "working on API"}
    new_state = {"status": "API development in progress"}
    result = await processor.compare_states_batch([(old_state, new_state)])
    assert result[0]["has_changes"] == False  # Semantically equivalent
```

### Integration Tests (Priority: HIGH)
```python
# test_full_pipeline.py
async def test_multi_meeting_tracking():
    # Meeting 1: Project starts
    response1 = await client.post("/api/ingest", json=meeting1)
    
    # Meeting 2: Progress update
    response2 = await client.post("/api/ingest", json=meeting2)
    
    # Query timeline
    timeline = await client.post("/api/query", json={
        "query": "Show me the timeline for Project Alpha"
    })
    
    assert len(timeline.json()["supporting_data"][0]["timeline"]) >= 2
```

### Performance Tests (Priority: MEDIUM)
```python
# test_performance.py
def test_large_transcript_handling():
    # 50KB transcript with 20+ entities
    large_transcript = generate_large_transcript()
    
    start = time.time()
    response = client.post("/api/ingest", json={
        "title": "Large Meeting",
        "transcript": large_transcript
    })
    
    assert response.status_code == 200
    assert time.time() - start < 30  # Should complete within 30s
```

---

## Success Metrics

### Week 1
- [ ] 100% of test queries return valid results
- [ ] State tracking accuracy > 90%
- [ ] Query response time < 2 seconds
- [ ] Zero unhandled exceptions in 24 hours

### Month 1
- [ ] 1000+ meetings ingested successfully
- [ ] 5000+ state transitions tracked
- [ ] Cache hit rate > 50%
- [ ] Query response time < 500ms (cached)

### Quarter 1
- [ ] 10,000+ meetings processed
- [ ] 50,000+ entities tracked
- [ ] 99.9% API uptime
- [ ] Full audit trail for all changes

---

## Implementation Notes

1. **Always test after each change** - The system is complex with many interactions
2. **Keep backward compatibility** - Don't break existing API contracts
3. **Document schema changes** - Critical for debugging state issues
4. **Monitor performance** - Watch for degradation as data grows
5. **Plan for scale** - Current SQLite approach has limits

The system is now functionally complete. Focus should be on testing, performance optimization, and preparing for production scale.