# Practical Action Plan: Get State Tracking Working
## Goal: Achieve working state tracking in 2-3 hours

Based on the forensic analysis, here's what we need to do RIGHT NOW to get a working system.

## Phase 1: Verify Basic Functionality (15 min)

### 1.1 Test Current State
```bash
# 1. Restart API with new model
# 2. Run test_via_api.py
# 3. Check if queries work with Claude model
```

**Expected**: Either queries work (great!) or we need to fix response format

### 1.2 Quick Fix if Queries Still Broken
```python
# In query_engine_v2.py, remove ALL response_format usage
# Just use simple prompts with "Respond with JSON containing answer and confidence"
```

## Phase 2: Implement Minimal State Tracking (1 hour)

### 2.1 Create Simple State Fetcher
**File**: `src/storage.py` - Add method:
```python
def get_all_current_states(self) -> Dict[str, Dict]:
    """Get current state for all entities as a simple dict."""
    conn = sqlite3.connect(self.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT e.name, e.type, es.state, es.timestamp
        FROM entities e
        LEFT JOIN entity_states es ON e.id = es.entity_id
        WHERE es.timestamp = (
            SELECT MAX(timestamp) 
            FROM entity_states 
            WHERE entity_id = e.id
        )
        OR es.timestamp IS NULL
    """)
    
    states = {}
    for row in cursor.fetchall():
        name, entity_type, state, timestamp = row
        states[f"{name}|{entity_type}"] = {
            "state": json.loads(state) if state else {},
            "timestamp": timestamp
        }
    
    conn.close()
    return states
```

### 2.2 Update Extractor to Use Prior States
**File**: `src/extractor.py` - Modify extract_meeting_info():
```python
async def extract_meeting_info(self, transcript: str, prior_states: Dict[str, Dict] = None) -> ExtractionResult:
    """Extract with prior states for comparison."""
    
    # Build prompt with prior states
    prior_states_text = ""
    if prior_states:
        prior_states_text = "\n\nPRIOR STATES OF ENTITIES:\n"
        for key, data in prior_states.items():
            name, entity_type = key.split("|")
            state = data["state"]
            prior_states_text += f"\n{name} ({entity_type}): {json.dumps(state)}"
    
    prompt = f"""Analyze this meeting transcript and extract...
    
{prior_states_text}

IMPORTANT: For each entity, compare its current state to the prior state above.
In the 'states' array, include ONLY entities that have changed state.

Transcript:
{transcript}
"""
    # Rest of extraction...
```

### 2.3 Update API Endpoint
**File**: `src/api.py` - Modify /api/ingest:
```python
@app.post("/api/ingest")
async def ingest_meeting(request: IngestRequest):
    # Get prior states BEFORE extraction
    prior_states = storage.get_all_current_states()
    
    # Pass to enhanced extractor
    extraction = await enhanced_extractor.extract_meeting_info(
        request.transcript,
        prior_states=prior_states
    )
    
    # Rest of processing...
```

## Phase 3: Add Simple State Detection (30 min)

### 3.1 Re-enable Pattern Detection
**File**: `src/processor.py` - Add simple patterns:
```python
def _detect_state_from_content(self, content: str, entity_name: str) -> Optional[Dict]:
    """Simple pattern-based state detection."""
    content_lower = content.lower()
    entity_lower = entity_name.lower()
    
    # Only if entity is mentioned
    if entity_lower not in content_lower:
        return None
    
    # Status patterns
    if f"{entity_lower} is now in progress" in content_lower:
        return {"status": "in_progress"}
    elif f"{entity_lower} is blocked" in content_lower:
        return {"status": "blocked"}
    elif f"{entity_lower} is complete" in content_lower:
        return {"status": "completed"}
    
    # Progress patterns
    import re
    progress_match = re.search(
        f"{entity_lower}.*?(\\d+)%", 
        content_lower
    )
    if progress_match:
        return {"progress": f"{progress_match.group(1)}%"}
    
    return None
```

## Phase 4: Minimal Testing (30 min)

### 4.1 Create Simple Test
**File**: `test_minimal_state_tracking.py`
```python
import requests
import json
import time

API_BASE = "http://localhost:8000"

# Meeting 1: Set initial states
meeting1 = {
    "title": "Initial Status",
    "transcript": "Project Alpha is in planning. It's at 0% progress."
}

print("Ingesting Meeting 1...")
resp = requests.post(f"{API_BASE}/api/ingest", json=meeting1)
print(f"Result: {resp.status_code}")
time.sleep(2)

# Meeting 2: Change states  
meeting2 = {
    "title": "Progress Update",
    "transcript": "Project Alpha is now in progress. It's at 30% complete."
}

print("Ingesting Meeting 2...")
resp = requests.post(f"{API_BASE}/api/ingest", json=meeting2)
print(f"Result: {resp.status_code}")

# Check transitions
resp = requests.get(f"{API_BASE}/api/entities")
entities = resp.json()
for e in entities:
    if "Alpha" in e["name"]:
        # Get timeline
        resp = requests.get(f"{API_BASE}/api/entities/{e['id']}/timeline")
        print(f"Timeline for {e['name']}: {resp.json()}")
```

## What We're NOT Doing (Yet)

1. **Complex batch processing** - Simple is better for now
2. **Fancy caching** - Premature optimization
3. **Multiple model fallbacks** - One working model is enough
4. **Semantic comparison** - String comparison is fine to start
5. **Email metadata extraction** - Core state tracking first

## Success Criteria

After these changes:
1. ✅ State transitions are created when things change
2. ✅ Timeline queries return actual history
3. ✅ Can track project progress over time
4. ✅ Can see when things get blocked/unblocked

## Time Estimate

- Phase 1: 15 minutes (test + quick fix)
- Phase 2: 1 hour (prior states implementation)
- Phase 3: 30 minutes (pattern detection)
- Phase 4: 30 minutes (testing)

**Total: 2 hours 15 minutes**

## Next Steps After This Works

1. Add email metadata extraction
2. Improve state inference patterns  
3. Add proper error handling
4. Implement caching for performance
5. Add comprehensive tests

But FIRST, we need basic state tracking to work!