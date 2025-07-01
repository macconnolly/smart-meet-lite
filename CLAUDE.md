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

## Dependencies

- Docker Desktop must be running for Qdrant vector database
- Python 3.11+ required
- ONNX model (~90MB) downloaded during setup
- OpenRouter API key needed for LLM extraction