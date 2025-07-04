"""Enhanced FastAPI REST API with business intelligence capabilities."""

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uvicorn
import logging
import json
import sqlite3

from .models import Meeting
from .extractor import MemoryExtractor
from .extractor_enhanced import EnhancedMeetingExtractor
from .embeddings import EmbeddingEngine
from .storage import MemoryStorage
from .processor import EntityProcessor
from .query_engine import QueryEngine
from .entity_resolver import EntityResolver
from .config import settings
import httpx
from openai import OpenAI

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
embeddings = EmbeddingEngine()

# Setup proxy configuration for corporate environments
proxies = None
if settings.https_proxy or settings.http_proxy:
    proxies = {}
    if settings.http_proxy:
        proxies["http://"] = settings.http_proxy
    if settings.https_proxy:
        proxies["https://"] = settings.https_proxy
    logger.info(f"Using proxy configuration: {proxies}")

# Create shared HTTP client with proxy and SSL configuration
http_client = httpx.Client(
    verify=settings.ssl_verify,
    proxies=proxies,
    timeout=30.0
)

# Create shared LLM client
llm_client = OpenAI(
    api_key=settings.openrouter_api_key,
    base_url=settings.openrouter_base_url,
    default_headers={
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Smart-Meet Lite"
    },
    http_client=http_client
)

# Create extractors - both basic and enhanced
extractor = MemoryExtractor()
enhanced_extractor = EnhancedMeetingExtractor(llm_client)

# Create cache and LLM processor for production use
from .cache import CacheLayer
from .llm_processor import LLMProcessor

cache = CacheLayer(default_ttl=3600)  # 1 hour cache
llm_processor = LLMProcessor(cache)

# Create shared EntityResolver
entity_resolver = EntityResolver(
    storage=storage,
    embeddings=embeddings,
    llm_client=llm_client,
    use_llm=settings.entity_resolution_use_llm
)

# Try to import production implementations first, fallback to original if not available
try:
    from .processor_v2 import EnhancedMeetingProcessor
    processor = EnhancedMeetingProcessor(storage, entity_resolver, embeddings, llm_processor)
    logger.info("Using production-ready processor_v2 with LLM batch processing")
except ImportError:
    from .processor import EntityProcessor
    processor = EntityProcessor(storage, entity_resolver)
    logger.warning("processor_v2 not found, using original processor")

try:
    from .query_engine_v2 import ProductionQueryEngine
    query_engine = ProductionQueryEngine(storage, embeddings, entity_resolver, llm_client)
    logger.info("Using production-ready query_engine_v2")
except ImportError:
    from .query_engine import QueryEngine
    query_engine = QueryEngine(storage, embeddings, entity_resolver)
    logger.warning("query_engine_v2 not found, using original query engine")


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

        # Use enhanced extractor for comprehensive intelligence
        # Pass email metadata if available
        email_metadata = {}
        if hasattr(request, 'email_metadata') and request.email_metadata:
            email_metadata = request.email_metadata
        
        extraction = enhanced_extractor.extract(
            request.transcript, 
            meeting.id,
            email_metadata=email_metadata
        )
        
        # Validate extraction produced data
        if not extraction.memories and not extraction.entities:
            # Check if this is a fallback
            extraction_method = extraction.meeting_metadata.get("extraction_method", "unknown")
            error_info = extraction.meeting_metadata.get("extraction_error", "No error details")
            
            if extraction_method == "basic_fallback":
                logger.warning(f"Enhanced extraction failed, using basic extraction. Error: {error_info}")
                # Add warning to meeting metadata
                meeting.metadata = {"extraction_warning": "Processed with basic extraction - data may be incomplete"}
                
                # If even basic extraction produced no data, this is critical
                if len(extraction.memories) == 0 and len(extraction.entities) == 0:
                    raise HTTPException(
                        status_code=500,
                        detail={
                            "error": "Both enhanced and basic extraction failed to produce any data",
                            "extraction_metadata": extraction.meeting_metadata,
                            "transcript_length": len(request.transcript),
                            "suggestion": "Check transcript format and LLM configuration"
                        }
                    )
            else:
                # Complete extraction failure
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Extraction failed to produce any data",
                        "extraction_metadata": extraction.meeting_metadata,
                        "suggestion": "Check LLM configuration and API keys"
                    }
                )

        # Update meeting with extracted metadata
        meeting.summary = extraction.summary
        meeting.topics = extraction.topics
        meeting.participants = extraction.participants
        meeting.key_decisions = extraction.decisions
        meeting.action_items = extraction.action_items
        meeting.memory_count = len(extraction.memories)
        
        # Update with enhanced metadata
        metadata = extraction.meeting_metadata
        meeting.email_metadata = {
            "from": metadata.get("email_from"),
            "to": metadata.get("email_to", []),
            "cc": metadata.get("email_cc", []),
            "date": metadata.get("email_date"),
            "subject": metadata.get("email_subject")
        }
        meeting.project_tags = metadata.get("project_tags", [])
        meeting.meeting_type = metadata.get("meeting_type")
        meeting.organization_context = metadata.get("organization_context")
        meeting.detailed_summary = metadata.get("detailed_summary", extraction.summary)
        
        # Parse actual times if provided
        if metadata.get("actual_start_time"):
            try:
                from datetime import datetime
                meeting.actual_start_time = datetime.fromisoformat(metadata["actual_start_time"])
            except:
                pass
        if metadata.get("actual_end_time"):
            try:
                from datetime import datetime
                meeting.actual_end_time = datetime.fromisoformat(metadata["actual_end_time"])
            except:
                pass

        # Save meeting with all metadata
        storage.save_meeting(meeting)
        
        # Store raw extraction for future reference
        storage.update_meeting_raw_extraction(meeting.id, {
            "entities": extraction.entities,
            "relationships": extraction.relationships,
            "states": extraction.states,
            "metadata": extraction.meeting_metadata,
            "detailed_summary": meeting.detailed_summary
        })
        
        # Save enhanced data to specialized tables
        enhanced_metadata = extraction.meeting_metadata
        
        # Save deliverables intelligence
        if enhanced_metadata.get("deliverables"):
            storage.save_meeting_deliverables(meeting.id, enhanced_metadata["deliverables"])
        
        # Save stakeholder intelligence
        if enhanced_metadata.get("stakeholder_intelligence"):
            storage.save_stakeholder_intelligence(meeting.id, enhanced_metadata["stakeholder_intelligence"])
        
        # Save decisions with context
        if enhanced_metadata.get("decisions_with_context"):
            storage.save_decisions_with_context(meeting.id, enhanced_metadata["decisions_with_context"])
        
        # Save risk areas
        implementation_insights = enhanced_metadata.get("implementation_insights", {})
        if implementation_insights.get("risk_areas"):
            storage.save_risk_areas(meeting.id, implementation_insights["risk_areas"])

        # Process entities, states, and relationships
        # Use the appropriate method based on processor type
        if hasattr(processor, 'process_meeting_with_context'):
            # Using enhanced processor v2
            processing_results = await processor.process_meeting_with_context(extraction, meeting.id)
        else:
            # Using original processor
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
        # Use the appropriate method based on query engine type
        if hasattr(query_engine, 'process_query'):
            # Using production query engine v2
            result = await query_engine.process_query(request.query)
        else:
            # Using original query engine
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


@app.get("/api/meetings/{meeting_id}/intelligence")
async def get_meeting_intelligence(meeting_id: str):
    """Get comprehensive intelligence for a meeting including deliverables, stakeholders, risks."""
    try:
        meeting = storage.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Get all enhanced data
        conn = storage.db_path
        import sqlite3
        db = sqlite3.connect(conn)
        cursor = db.cursor()
        
        # Get deliverables
        cursor.execute("SELECT * FROM meeting_deliverables WHERE meeting_id = ?", (meeting_id,))
        deliverables = []
        for row in cursor.fetchall():
            deliverables.append({
                "name": row[2],
                "type": row[3],
                "target_audience": json.loads(row[4]) if row[4] else [],
                "requirements": json.loads(row[5]) if row[5] else [],
                "discussed_evolution": row[6],
                "dependencies": json.loads(row[7]) if row[7] else [],
                "deadline": row[8],
                "format_preferences": row[9]
            })
        
        # Get stakeholder intelligence
        cursor.execute("SELECT * FROM stakeholder_intelligence WHERE meeting_id = ?", (meeting_id,))
        stakeholders = []
        for row in cursor.fetchall():
            stakeholders.append({
                "stakeholder": row[2],
                "role": row[3],
                "communication_preferences": row[4],
                "noted_concerns": json.loads(row[5]) if row[5] else [],
                "format_preferences": row[6],
                "questions_asked": json.loads(row[7]) if row[7] else [],
                "key_interests": json.loads(row[8]) if row[8] else []
            })
        
        # Get decisions with context
        cursor.execute("SELECT * FROM decisions_with_context WHERE meeting_id = ?", (meeting_id,))
        decisions = []
        for row in cursor.fetchall():
            decisions.append({
                "decision": row[2],
                "rationale": row[3],
                "stakeholders_involved": json.loads(row[4]) if row[4] else [],
                "impact_areas": json.loads(row[5]) if row[5] else [],
                "supersedes_decision": row[6],
                "decision_status": row[7]
            })
        
        # Get risks
        cursor.execute("SELECT * FROM risk_areas WHERE meeting_id = ?", (meeting_id,))
        risks = []
        for row in cursor.fetchall():
            risks.append({
                "risk": row[2],
                "severity": row[3],
                "mitigation_approach": row[4]
            })
        
        db.close()
        
        return {
            "meeting": {
                "id": meeting.id,
                "title": meeting.title,
                "date": meeting.date,
                "summary": meeting.summary,
                "detailed_summary": meeting.detailed_summary,
                "meeting_type": meeting.meeting_type,
                "project_tags": meeting.project_tags
            },
            "intelligence": {
                "deliverables": deliverables,
                "stakeholder_intelligence": stakeholders,
                "decisions_with_context": decisions,
                "risk_areas": risks,
                "total_entities": meeting.entity_count,
                "total_memories": meeting.memory_count
            }
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error getting meeting intelligence: {traceback.format_exc()}")
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


@app.get("/health/detailed")
async def detailed_health_check():
    """Comprehensive system health check."""
    health_status = {
        "status": "checking",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check LLM configuration
    try:
        model_name = settings.clean_openrouter_model
        raw_model = settings.openrouter_model
        health_status["checks"]["llm_config"] = {
            "status": "ok",
            "raw_model": raw_model,
            "clean_model": model_name,
            "has_comment": '#' in raw_model,
            "has_whitespace": raw_model != raw_model.strip()
        }
    except Exception as e:
        health_status["checks"]["llm_config"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Test LLM connectivity
    try:
        test_response = llm_client.chat.completions.create(
            model=settings.clean_openrouter_model,
            messages=[{"role": "user", "content": "Say 'ok'"}],
            max_tokens=10
        )
        health_status["checks"]["llm_connectivity"] = {
            "status": "ok",
            "model_used": settings.clean_openrouter_model,
            "response": test_response.choices[0].message.content
        }
    except Exception as e:
        health_status["checks"]["llm_connectivity"] = {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "model_attempted": settings.clean_openrouter_model
        }
    
    # Check Qdrant
    try:
        info = storage.qdrant.get_collection(storage.collection_name)
        health_status["checks"]["qdrant"] = {
            "status": "ok",
            "collection": storage.collection_name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count
        }
    except Exception as e:
        health_status["checks"]["qdrant"] = {
            "status": "error",
            "error": str(e),
            "collection_name": storage.collection_name
        }
    
    # Check database
    try:
        conn = sqlite3.connect(storage.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM memories")
        memory_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM meetings")
        meeting_count = cursor.fetchone()[0]
        conn.close()
        
        health_status["checks"]["database"] = {
            "status": "ok",
            "path": storage.db_path,
            "entity_count": entity_count,
            "memory_count": memory_count,
            "meeting_count": meeting_count
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e),
            "path": storage.db_path
        }
    
    # Check embeddings
    try:
        test_text = "test"
        test_embedding = embeddings.encode([test_text])
        health_status["checks"]["embeddings"] = {
            "status": "ok",
            "model_path": settings.onnx_model_path,
            "embedding_dim": test_embedding.shape[1] if len(test_embedding.shape) > 1 else test_embedding.shape[0]
        }
    except Exception as e:
        health_status["checks"]["embeddings"] = {
            "status": "error", 
            "error": str(e),
            "model_path": settings.onnx_model_path
        }
    
    # Overall status
    all_ok = all(check.get("status") == "ok" for check in health_status["checks"].values())
    health_status["status"] = "healthy" if all_ok else "unhealthy"
    
    # Add warnings if using fallback extraction
    warnings = []
    if health_status["checks"]["llm_connectivity"].get("status") == "error":
        warnings.append("LLM connectivity failed - system will use basic extraction")
    if warnings:
        health_status["warnings"] = warnings
    
    return health_status


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    logger.info("=== Smart-Meet Lite Production System Starting ===")
    logger.info(f"Using LLM Processor with {len(llm_processor.MODELS)} fallback models")
    logger.info(f"Cache initialized with {cache.default_ttl}s TTL")
    logger.info(f"Database path: {storage.db_path}")
    logger.info(f"Qdrant collection: {storage.collection_name}")
    
    # Log which components are being used
    if "processor_v2" in str(type(processor)):
        logger.info("✓ Using enhanced processor v2 with batch state comparison")
    if "ProductionQueryEngine" in str(type(query_engine)):
        logger.info("✓ Using production query engine")
    
    logger.info("=== System Ready ===")


def main():
    """Run the API server."""
    uvicorn.run(
        "src.api:app", host=settings.api_host, port=settings.api_port, reload=True
    )


if __name__ == "__main__":
    main()
