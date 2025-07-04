# Smart-Meet Lite Architecture Guide

## Overview

Smart-Meet Lite is an intelligent meeting memory system that extracts structured information from meeting transcripts, tracks entity states over time, and enables sophisticated business intelligence queries. This guide traces the complete flow from transcript ingestion to query results.

## System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   FastAPI       │────▶│  LLM Processor   │────▶│    Storage       │
│   (api.py)      │     │ (OpenRouter API) │     │  (SQLite/Qdrant) │
└─────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                         │
        ▼                        ▼                         ▼
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Extractor     │     │ Entity Resolver  │     │  Query Engine    │
│ (extractor.py)  │     │(entity_resolver) │     │ (query_engine)   │
└─────────────────┘     └──────────────────┘     └──────────────────┘
```

## Complete Request Flow

### 1. Meeting Ingestion (`POST /api/ingest`)

**Input**: Meeting transcript with title, content, and date

**Step-by-Step Flow**:

1. **API Receipt** (`src/api.py:IngestRequest`)
   - Validates request format
   - Creates unique meeting ID
   - Initiates processing pipeline

2. **Enhanced Extraction** (`src/extractor_enhanced.py:EnhancedMeetingExtractor`)
   - Sends transcript to LLM (OpenRouter) with structured prompt
   - Extracts:
     - Entities (people, projects, features, systems)
     - Current states (status, progress, blockers, assignments)
     - Relationships (owns, responsible_for, depends_on)
     - Action items and decisions
   - Returns `ExtractionResult` object

3. **Entity Resolution** (`src/entity_resolver.py:EntityResolver`)
   For each extracted entity:
   - Searches existing entities by name+type
   - If similarity > threshold (60%): links to existing entity
   - If no match: creates new entity
   - Updates entity attributes

4. **State Processing** (`src/processor_v2.py:EnhancedMeetingProcessor`)
   
   **CURRENT ISSUE**: Creates transitions for new entities (null → initial state)
   
   **CORRECT BEHAVIOR**:
   ```python
   For each entity with state information:
       if entity has no prior states in database:
           # First time seeing this entity
           entity.current_state = extracted_state
           # NO transition created
       else:
           # Entity has history
           previous_state = get_latest_state(entity)
           if state_has_changed(previous_state, extracted_state):
               create_transition(
                   from_state=previous_state,
                   to_state=extracted_state,
                   reason=generate_reason()
               )
               entity.current_state = extracted_state
   ```

5. **Storage** (`src/storage.py:MemoryStorage`)
   - Saves entities to SQLite (`entities` table)
   - Saves relationships to SQLite (`entity_relationships` table)
   - Saves state transitions to SQLite (`state_transitions` table)
   - Creates embeddings and saves to Qdrant for semantic search

### 2. State Tracking Deep Dive

**State Transition Logic**:

```python
# What happens now (INCORRECT):
entity = Entity(name="Authentication Module", type="feature")
# First meeting: "Authentication Module is in planning"
state_1 = {"status": "in planning", "assigned_to": "John"}
transition_1 = StateTransition(
    from_state=None,  # Wrong! Entity didn't come from nothing
    to_state=state_1,
    reason="Initial state captured"
)

# What should happen (CORRECT):
entity = Entity(
    name="Authentication Module", 
    type="feature",
    current_state=state_1  # Just set the state
)
# No transition created for first observation
```

**State Change Detection**:

The system uses intelligent comparison:
- Ignores semantic equivalents ("30%" vs "30% complete")
- Detects real changes ("30%" vs "50%")
- Tracks field additions/removals
- Uses LLM for nuanced comparison via `LLMProcessor.compare_states_batch()`

### 3. Business Intelligence Queries (`POST /api/query`)

**Query Processing Flow**:

1. **Query Analysis** (`src/query_engine_v2.py`)
   - Determines query type (status, ownership, timeline, dependencies)
   - Extracts entity references
   - Identifies time constraints

2. **Data Retrieval**
   - Fetches relevant entities
   - Loads relationships
   - Retrieves state history
   - Gets associated memories

3. **Insight Generation**
   - Analyzes patterns across meetings
   - Identifies trends and risks
   - Generates recommendations

### 4. Semantic Search (`POST /api/search`)

1. **Vector Creation**
   - Converts query to embedding using ONNX model
   - Searches Qdrant for similar memories

2. **Entity Enhancement**
   - Links memories to entities
   - Provides context from entity states

## Key Design Decisions

### Why Track States, Not Just Memories?

Traditional meeting tools just store transcript snippets. Smart-Meet Lite maintains a living model of your organization:

- **Entities persist** across meetings (Project Alpha is the same project in January and February)
- **States evolve** over time (planned → in progress → blocked → completed)  
- **Relationships matter** (John owns Authentication, which blocks Frontend)

### Entity Resolution Strategy

We use a hybrid approach:
1. **Embedding similarity** for initial matching (via local ONNX model)
2. **Name/type exact matching** for precision
3. **LLM fallback** for complex cases

This prevents duplicate entities while maintaining accuracy.

### State vs. Transition

- **State**: The current snapshot of an entity's properties
- **Transition**: A recorded change from one state to another

Only transitions tell the story of how things changed and why.

## Common Patterns

### Pattern 1: Project Status Meeting
```
Input: "The authentication module is now 50% complete"
Process:
1. Extract: Entity="authentication module", State={progress: "50%"}
2. Resolve: Find existing "authentication module" entity
3. Compare: Previous state had progress="30%"
4. Transition: Create transition with reason="Progress increased from 30% to 50%"
```

### Pattern 2: New Assignment
```
Input: "Sarah will take over the API design from Mike"
Process:
1. Extract: Relationship change for "API design"
2. Deactivate: Old relationship (Mike → API design)
3. Create: New relationship (Sarah → API design)
4. Track: Ownership transition
```

## Database Schema

### Core Tables

```sql
-- Entities (persistent objects)
entities:
  - id: UUID
  - name: TEXT
  - type: TEXT (person|project|feature|task|system)
  - current_state: JSON
  - created_at: TIMESTAMP

-- State Transitions (change history)
state_transitions:
  - id: UUID
  - entity_id: UUID
  - from_state: JSON (NULL for initial states - TO BE FIXED)
  - to_state: JSON
  - changed_fields: JSON[]
  - reason: TEXT
  - meeting_id: UUID
  - timestamp: TIMESTAMP

-- Entity Relationships (who owns what)
entity_relationships:
  - id: UUID
  - from_entity_id: UUID
  - to_entity_id: UUID
  - relationship_type: TEXT
  - active: BOOLEAN
  - meeting_id: UUID
```

## Configuration & Models

### LLM Configuration
- Primary model: Defined in `OPENROUTER_MODEL` env var
- Fallback chain in `LLMProcessor.MODELS`
- SSL verification disabled for corporate firewalls

### Entity Resolution
- Threshold: 60% similarity (configurable)
- Auto-creation of deliverables on assignment
- LLM fallback enabled by default

## Future Improvements

1. **Fix State Tracking**: Implement correct initial state handling (no null transitions)
2. **Add Confidence Scores**: Track extraction confidence
3. **Implement State Merging**: Handle conflicting information gracefully
4. **Add Audit Trail**: Track all system decisions
5. **Enhance Timeline API**: Add filtering and aggregation options

## Debugging Tips

### Check State Tracking
```bash
# See all transitions for an entity
curl http://localhost:8000/api/entities/{entity_id}/timeline

# Should see:
# - No transition for first occurrence
# - Transitions only for actual changes
```

### Verify Entity Resolution
```bash
# List all entities
curl http://localhost:8000/api/entities

# Check for duplicates (same name, same type)
```

### Monitor LLM Usage
```python
# In Python
processor.get_stats()  # Shows cache hits, fallback usage
```

## Common Issues

1. **"Why are all fields marked as changed?"**
   - First entity observation incorrectly creates transition from null

2. **"Why didn't it track the state change?"**
   - Check if states are semantically equivalent
   - Verify entity resolution didn't create duplicate

3. **"Search isn't finding relevant results"**
   - Check embedding generation
   - Verify Qdrant is running