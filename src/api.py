"""Enhanced FastAPI REST API with business intelligence capabilities."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import logging

from .models import Meeting
from .extractor import MemoryExtractor
from .embeddings import EmbeddingEngine
from .storage import MemoryStorage
from .processor import EntityProcessor
from .query_engine import QueryEngine
from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Smart-Meet Lite",
    description="Meeting memory extraction with business intelligence",
    version="2.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
storage = MemoryStorage()
extractor = MemoryExtractor()
embeddings = EmbeddingEngine()
processor = EntityProcessor(storage)
query_engine = QueryEngine(storage, embeddings)


# Request/Response models
class IngestRequest(BaseModel):
    title: str
    transcript: str
    date: Optional[datetime] = None


class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    meeting_id: Optional[str] = None
    entity_filter: Optional[List[str]] = None


class BIQueryRequest(BaseModel):
    query: str


class MeetingResponse(BaseModel):
    id: str
    title: str
    summary: Optional[str]
    participants: List[str]
    topics: List[str]
    decisions: List[str]
    action_items: List[Dict[str, Any]]
    memory_count: int
    entity_count: int
    created_at: datetime


class EntityResponse(BaseModel):
    id: str
    type: str
    name: str
    current_state: Optional[Dict[str, Any]]
    attributes: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    last_updated: datetime


class MemoryResponse(BaseModel):
    id: str
    content: str
    speaker: Optional[str]
    timestamp: Optional[str]
    metadata: Dict[str, Any]
    entity_mentions: List[str]
    meeting_id: str
    meeting_title: Optional[str]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Smart-Meet Lite",
        "version": "2.0.0",
        "features": ["memory_extraction", "entity_tracking", "business_intelligence"],
    }


@app.post("/api/ingest", response_model=MeetingResponse)
async def ingest_meeting(request: IngestRequest):
    """Ingest a meeting transcript and extract business intelligence."""
    try:
        # Create meeting object
        meeting = Meeting(
            title=request.title, transcript=request.transcript, date=request.date
        )

        # Extract comprehensive intelligence using LLM
        extraction = extractor.extract(request.transcript, meeting.id)

        # Update meeting with extracted metadata
        meeting.summary = extraction.summary
        meeting.topics = extraction.topics
        meeting.participants = extraction.participants
        meeting.key_decisions = extraction.decisions
        meeting.action_items = extraction.action_items
        meeting.memory_count = len(extraction.memories)

        # Save meeting
        storage.save_meeting(meeting)

        # Process entities, states, and relationships
        processing_results = processor.process_extraction(extraction, meeting.id)
        meeting.entity_count = len(processing_results["entity_map"])

        # Generate embeddings for memories
        if extraction.memories:
            memory_texts = [m.content for m in extraction.memories]
            memory_embeddings = embeddings.encode_batch(memory_texts)

            # Save memories with embeddings
            storage.save_memories(extraction.memories, memory_embeddings)

        return MeetingResponse(
            id=meeting.id,
            title=meeting.title,
            summary=meeting.summary,
            participants=meeting.participants,
            topics=meeting.topics,
            decisions=meeting.key_decisions,
            action_items=meeting.action_items,
            memory_count=meeting.memory_count,
            entity_count=meeting.entity_count,
            created_at=meeting.created_at,
        )

    except Exception as e:
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}"
        logger.error(f"Ingestion failed: {error_details}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_details)


@app.post("/api/search", response_model=Dict[str, Any])
async def search_memories(request: SearchRequest):
    """Search for similar memories with entity filtering."""
    try:
        # Generate query embedding
        query_embedding = embeddings.encode(request.query)

        # Ensure embedding is 1D (encode returns [1, 384] for single text)
        if query_embedding.ndim > 1:
            query_embedding = query_embedding[0]

        # Build filters
        filters = {}
        if request.meeting_id:
            filters["meeting_id"] = request.meeting_id
        if request.entity_filter:
            # Resolve entity names to IDs
            entity_ids = []
            for entity_name in request.entity_filter:
                entity = storage.get_entity_by_name(entity_name)
                if entity:
                    entity_ids.append(entity.id)
            if entity_ids:
                filters["entity_mentions"] = entity_ids

        # Search
        results = storage.search(query_embedding, limit=request.limit, filters=filters)

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "memory": {
                        "id": result.memory.id,
                        "content": result.memory.content,
                        "speaker": result.memory.speaker,
                        "timestamp": result.memory.timestamp,
                        "metadata": result.memory.metadata,
                        "entity_mentions": [e.name for e in result.relevant_entities],
                        "meeting_id": result.memory.meeting_id,
                        "meeting_title": (
                            result.meeting.title if result.meeting else None
                        ),
                    },
                    "score": result.score,
                    "distance": result.distance,
                    "entities": [
                        {"id": e.id, "name": e.name, "type": e.type}
                        for e in result.relevant_entities
                    ],
                }
            )

        return {
            "results": formatted_results,
            "query": request.query,
            "count": len(results),
            "filters_applied": filters,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query", response_model=Dict[str, Any])
async def business_intelligence_query(request: BIQueryRequest):
    """Answer business intelligence questions."""
    try:
        # Process query through query engine
        result = query_engine.answer_query(request.query)

        return {
            "query": result.query,
            "answer": result.answer,
            "confidence": result.confidence,
            "intent": {
                "type": result.intent.intent_type,
                "entities": result.intent.entities,
                "filters": result.intent.filters,
            },
            "supporting_data": result.supporting_data,
            "entities_involved": [
                {"id": e.id, "name": e.name, "type": e.type}
                for e in result.entities_involved
            ],
            "visualizations": result.visualizations,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities", response_model=List[EntityResponse])
async def list_entities(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search: Optional[str] = Query(None, description="Search entities by name"),
):
    """List all entities with optional filtering."""
    try:
        if search:
            entities = storage.search_entities(search, entity_type)
        else:
            # Get all entities (would need to implement this in storage)
            entities = storage.search_entities("", entity_type)

        responses = []
        for entity in entities:
            # Get current state and relationships
            current_state = storage.get_entity_current_state(entity.id)
            relationships = storage.get_entity_relationships(entity.id)

            responses.append(
                EntityResponse(
                    id=entity.id,
                    type=entity.type,
                    name=entity.name,
                    current_state=current_state,
                    attributes=entity.attributes,
                    relationships=relationships,
                    last_updated=entity.last_updated,
                )
            )

        return responses

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities/{entity_id}")
async def get_entity_details(entity_id: str):
    """Get detailed information about a specific entity."""
    try:
        # This would need to be implemented in storage
        # For now, return a placeholder
        raise HTTPException(status_code=501, detail="Not implemented yet")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities/{entity_id}/timeline")
async def get_entity_timeline(entity_id: str):
    """Get timeline of state changes for an entity."""
    try:
        timeline = storage.get_entity_timeline(entity_id)
        return {
            "entity_id": entity_id,
            "timeline": timeline,
            "total_changes": len(timeline),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/{metric}")
async def get_analytics(
    metric: str,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """Get analytics data for various metrics."""
    try:
        time_range = None
        if start_date and end_date:
            time_range = (start_date, end_date)

        data = storage.get_analytics_data(metric, time_range)

        return {
            "metric": metric,
            "data": data,
            "time_range": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/meetings", response_model=List[MeetingResponse])
async def list_meetings():
    """List all meetings."""
    try:
        meetings = storage.get_all_meetings()
        return [
            MeetingResponse(
                id=m.id,
                title=m.title,
                summary=m.summary,
                participants=m.participants,
                topics=m.topics,
                decisions=m.key_decisions,
                action_items=m.action_items,
                memory_count=m.memory_count,
                entity_count=m.entity_count,
                created_at=m.created_at,
            )
            for m in meetings
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    """Get a specific meeting with its memories and entities."""
    try:
        meeting = storage.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        memories = storage.get_memories_by_meeting(meeting_id)

        # Get unique entities mentioned in this meeting
        entity_ids = set()
        for memory in memories:
            entity_ids.update(memory.entity_mentions)

        entities = []
        for entity_id in entity_ids:
            # Would need to implement get_entity_by_id in storage
            pass

        return {
            "meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "summary": meeting.summary,
                "participants": meeting.participants,
                "topics": meeting.topics,
                "decisions": meeting.key_decisions,
                "action_items": meeting.action_items,
                "memory_count": meeting.memory_count,
                "entity_count": meeting.entity_count,
                "created_at": meeting.created_at,
            },
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "speaker": m.speaker,
                    "timestamp": m.timestamp,
                    "metadata": m.metadata,
                    "entity_mentions": m.entity_mentions,
                }
                for m in memories
            ],
            "entities_mentioned": entities,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/file", response_model=MeetingResponse)
async def ingest_file(file: UploadFile = File(...), title: Optional[str] = None):
    """Ingest a meeting transcript from file upload."""
    try:
        # Read file content
        content = await file.read()
        transcript = content.decode("utf-8")

        # Use filename as title if not provided
        if not title:
            title = file.filename.replace(".txt", "").replace("_", " ").title()

        # Process as regular ingestion
        request = IngestRequest(title=title, transcript=transcript)
        return await ingest_meeting(request)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the API server."""
    uvicorn.run(
        "src.api:app", host=settings.api_host, port=settings.api_port, reload=True
    )


if __name__ == "__main__":
    main()
