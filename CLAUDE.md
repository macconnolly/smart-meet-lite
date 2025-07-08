# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Smart-Meet Lite is an intelligent meeting memory system with business intelligence capabilities. It extracts structured information from meeting transcripts, tracks entities (people, projects, features, deadlines), monitors state changes, and enables sophisticated querying of organizational knowledge.

## Architecture

The system uses a dual-storage architecture:
- **SQLite** for structured entity data, relationships, and state transitions
- **Qdrant** vector database for semantic search and similarity matching

Key components:
- **FastAPI** REST API (`src/api.py`)
- **LLM-based extraction** via OpenRouter (`src/extractor.py`)
- **Entity processing** and state management (`src/processor.py`)
- **Business intelligence query engine** (`src/query_engine.py`)
- **Local ONNX embeddings** for vector generation (`src/embeddings.py`)

## Essential Commands

### Development
```bash
# Start all services (requires Docker running)
make run          # Start API server on http://localhost:8000
make dev          # Start with auto-reload for development
make demo         # Run full business intelligence demo
make test         # Run system tests
```

### Setup & Maintenance
```bash
make setup        # Complete setup (installs deps, downloads model, inits DB)
make reset        # Reset database (WARNING: deletes all data)
make clean        # Clean cache files
make status       # Check if services are running
```

### Windows-specific
```bash
setup_windows.bat    # Automated Windows setup
start_windows.bat    # Start all services on Windows
```

### Testing
```bash
python test_bi_system.py    # Test core business intelligence features
python bi_demo.py           # Run comprehensive demo with sample data
python example.py           # Simple usage examples
make test-api              # Test API endpoints with curl
```

## Configuration

The system requires a `.env` file (copy from `.env.example`):
- `OPENROUTER_API_KEY` - Required for LLM extraction
- `OPENROUTER_MODEL` - Default: `anthropic/claude-3-haiku`
- `DATABASE_PATH` - SQLite database location
- `QDRANT_HOST/PORT` - Vector database connection

## Key API Endpoints

- `POST /api/ingest` - Ingest meeting transcript with entity extraction
- `POST /api/query` - Business intelligence queries (status, ownership, timelines)
- `POST /api/search` - Semantic search with entity filtering
- `GET /api/entities` - List all tracked entities
- `GET /api/entities/{id}/timeline` - Entity state history
- Interactive docs at `/docs`

## Development Notes

1. **Entity Extraction**: Uses LLM to identify people, projects, features, deadlines, and their relationships from meeting transcripts
2. **State Tracking**: Monitors entity states (planned, in_progress, blocked, completed) with transition history
3. **Relationship Mapping**: Tracks ownership, dependencies, and assignments between entities
4. **Query Processing**: Handles natural language queries about status, ownership, timelines, and analytics

## Query Engine MVP Fixes (CRITICAL - Start Here)

The system currently has a critical bug where ALL query operations fail with HTTP 500 errors. Follow these steps to fix:

### 1. Review the Roadmap
Read `018_Current_Plan.md` for the complete implementation guide with exact line numbers and code changes.

### 2. Implementation Order
1. **Phase 1: String Formatting Fix** (30 min) - Replace f-strings with concatenation in 7 methods
2. **Phase 2: State Normalization** (1 hour) - Add normalization at storage layer + migration
3. **Phase 3: Entity Extraction** (45 min) - Add stop word filtering
4. **Phase 4: Response Conciseness** (30 min) - Update prompts for brief answers
5. **Phase 5: Query Caching** (1 hour) - Add 5-minute cache
6. **Phase 6-8: Additional Fixes** (1 hour) - Async, indexes, cleanup

### 3. Critical Implementation Notes

**String Formatting (Phase 1)**:
- MUST replace ALL f-strings in query_engine_v2.py prompt generation
- Use string concatenation to avoid % format specifier errors
- Test with: `curl -X POST http://localhost:8000/api/query -d '{"query": "Status of 50% milestone?"}'`

**State Normalization (Phase 2)**:
- ALWAYS backup database before migration: `cp data/memories.db data/memories.db.backup`
- Run migration AFTER code changes: `python scripts/normalize_existing_states.py`
- Verify with queries - should not see "capitalization changes" messages

**Entity Extraction (Phase 3)**:
- The stop words list is comprehensive - includes months, question words, common verbs
- Test with: `python tests/test_entity_extraction.py`
- "What", "December", "Status" should NOT be extracted as entities

**OpenRouter Requirements**:
- DO NOT remove the direct `requests` usage in `_call_openrouter_api`
- This is required for structured output with OpenRouter
- The method MUST stay as-is for JSON schema validation

### 4. Testing Each Fix

After each phase:
```bash
# Test the specific fix
python tests/test_[phase_name].py

# Test query functionality
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the status of Project Alpha?"}'

# Run integration test after all fixes
python tests/test_mvp_integration.py
```

### 5. Expected Improvements

- **Before**: All queries return 500 errors
- **After**: All queries return 200 with valid JSON
- **Performance**: 2x+ faster for cached queries
- **Cost**: 60% reduction through caching
- **Quality**: Responses under 100 words, no verbose explanations

### 6. Common Pitfalls to Avoid

- Don't skip the database backup before migration
- Don't modify the OpenRouter API call structure
- Don't use f-strings in the prompt generation after Phase 1
- Don't forget to make handlers async in Phase 6
- Test each phase independently before moving to the next

## Dependencies

- Docker Desktop must be running for Qdrant vector database
- Python 3.11+ required
- ONNX model (~90MB) downloaded during setup
- OpenRouter API key needed for LLM extraction

## Current Status & Known Issues

**Status**: Data ingestion works perfectly, but ALL query operations fail with HTTP 500 errors.

**Root Causes**:
1. String formatting bug when entity data contains % characters
2. State normalization issues ("in_progress" vs "In Progress")
3. Common words extracted as entities ("What", "December")
4. Verbose responses instead of concise answers

**Solution**: Follow the Query Engine MVP Fixes above or see `018_Current_Plan.md` for detailed implementation.