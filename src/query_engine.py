"""Query engine for business intelligence questions."""

import json
import re
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from openai import OpenAI
import httpx
import warnings
from .models import QueryIntent, BIQueryResult, EntityMatch
from .storage import MemoryStorage
from .embeddings import EmbeddingEngine
from .entity_resolver import EntityResolver
from .config import settings

# Suppress SSL warnings in corporate environments
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

# Configure logging
logger = logging.getLogger(__name__)

class QueryEngine:
    """Simplified query engine with centralized entity resolution."""

    def __init__(self, storage: MemoryStorage, embeddings: EmbeddingEngine):
        """Initialize with storage and embedding engine."""
        self.storage = storage
        self.embeddings = embeddings
        
        # Create HTTP client with SSL verification disabled for corporate networks
        http_client = httpx.Client(verify=False)
        
        self.client = OpenAI(
            api_key=settings.openrouter_api_key, 
            base_url=settings.openrouter_base_url,
            default_headers={
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "Smart-Meet Lite",
            },
            http_client=http_client
        )
        
        # Initialize entity resolver with error handling
        try:
            self.entity_resolver = EntityResolver(
                storage=storage,
                embeddings=embeddings,
                llm_client=self.client
            )
        except Exception as e:
            logger.error(f"Failed to initialize EntityResolver: {e}")
            logger.warning("Entity resolution will be limited to exact matches")
            self.entity_resolver = None

    def parse_intent(self, query: str) -> QueryIntent:
        """Parse user query to understand intent."""
        prompt = """You are an expert at parsing user queries to understand their intent.
Analyze the user's query and extract the intent and any entities mentioned.

**CRITICAL INSTRUCTIONS:**
1.  **Extract Full Entity Names:** Identify and extract the complete names of any entities mentioned. Do not shorten or change them.
2.  **Be Exact:** The "entities" field in your JSON response must contain the exact strings from the query.

**EXAMPLE:**
- **Query:** "What is the current status of the mobile app redesign project?"
- **Correct Entities:** `["mobile app redesign project"]`
- **Incorrect Entities:** `["redesign project"]`, `["mobile app"]`

Intent types:
- status: Asking about current status/state of something
- ownership: Who owns/is responsible for something
- timeline: How something changed over time
- search: General search for information
- relationship: How entities are related
- analytics: Aggregate data or metrics

Return JSON:
{
  "intent_type": "status|ownership|timeline|search|relationship|analytics",
  "entities": ["full entity names exactly as mentioned in the query"],
  "filters": {
    "time_range": "last_week|last_month|q1|all_time",
    "entity_type": "project|feature|person|etc",
    "relationship_type": "owns|works_on|etc"
  },
  "aggregation": "count|sum|average|none"
}"""

        try:
            response = self.client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            # Log raw response for debugging
            raw_content = response.choices[0].message.content
            logger.info(f"Raw LLM response for intent parsing: {raw_content[:500] if raw_content else 'EMPTY'}")
            
            # Handle empty responses
            if not raw_content or raw_content.strip() == "":
                raise ValueError("LLM returned empty content")
            
            # Handle markdown-wrapped JSON
            if "```json" in raw_content:
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', raw_content, re.DOTALL)
                if json_match:
                    raw_content = json_match.group(1)
                    logger.debug("Extracted JSON from markdown block")
            
            data = json.loads(raw_content.strip())

            # Parse time range if specified
            time_range = None
            if data.get("filters", {}).get("time_range"):
                time_range = self._parse_time_range(data["filters"]["time_range"])

            return QueryIntent(
                intent_type=data["intent_type"],
                entities=data.get("entities", []),
                filters=data.get("filters", {}),
                time_range=time_range,
                aggregation=data.get("aggregation"),
            )

        except Exception as e:
            logger.error(f"Failed to parse intent: {e}")
            # Return a default search intent if parsing fails
            return QueryIntent(
                intent_type="search",
                entities=[],
                filters={},
                time_range=None,
                aggregation=None
            )


    def _parse_time_range(self, time_str: str) -> Dict[str, datetime]:
        """Parse time range string to datetime objects."""
        now = datetime.now()

        if time_str == "last_week":
            return {"start": now - timedelta(weeks=1), "end": now}
        elif time_str == "last_month":
            return {"start": now - timedelta(days=30), "end": now}
        elif time_str.startswith("q"):
            # Parse quarter
            quarter = int(time_str[1])
            year = now.year
            quarter_starts = {
                1: datetime(year, 1, 1),
                2: datetime(year, 4, 1),
                3: datetime(year, 7, 1),
                4: datetime(year, 10, 1),
            }
            quarter_ends = {
                1: datetime(year, 3, 31),
                2: datetime(year, 6, 30),
                3: datetime(year, 9, 30),
                4: datetime(year, 12, 31),
            }
            return {
                "start": quarter_starts.get(quarter, now),
                "end": quarter_ends.get(quarter, now),
            }

        return {"start": datetime.min, "end": now}


    def answer_query(self, query: str) -> BIQueryResult:
        """Answer a business intelligence query."""
        # Parse intent
        intent = self.parse_intent(query)
        
        # Pre-resolve all entities mentioned in the query
        if self.entity_resolver:
            entity_matches = self.entity_resolver.resolve_entities(
                intent.entities, 
                context=query
            )
        else:
            # Fallback to simple exact matching
            entity_matches = {}
            for term in intent.entities:
                entity = self.storage.get_entity_by_name(term)
                if entity:
                    entity_matches[term] = EntityMatch(
                        query_term=term,
                        entity=entity,
                        confidence=1.0,
                        match_type='exact'
                    )
                else:
                    entity_matches[term] = EntityMatch(
                        query_term=term,
                        entity=None,
                        confidence=0.0,
                        match_type='none'
                    )
        
        # Extract successfully resolved entities
        resolved_entities = {
            term: match.entity 
            for term, match in entity_matches.items() 
            if match.entity is not None
        }
        
        # Log resolution results
        logger.info(
            f"Entity resolution: {len(resolved_entities)}/{len(intent.entities)} resolved. "
            f"Matches: {[(t, m.entity.name if m.entity else None, m.confidence) 
                        for t, m in entity_matches.items()]}"
        )
        
        # Route to appropriate handler with resolved entities
        handler_params = {
            'query': query,
            'intent': intent,
            'resolved_entities': resolved_entities,
            'entity_matches': entity_matches  # Include confidence scores
        }
        
        handlers = {
            'status': self._answer_status_query,
            'ownership': self._answer_ownership_query,
            'timeline': self._answer_timeline_query,
            'relationship': self._answer_relationship_query,
            'analytics': self._answer_analytics_query,
            'search': self._answer_search_query
        }
        
        handler = handlers.get(intent.intent_type, self._answer_search_query)
        return handler(**handler_params)

    def _answer_status_query(self, 
                           query: str, 
                           intent: QueryIntent,
                           resolved_entities: Dict[str, Any],
                           entity_matches: Dict[str, EntityMatch]) -> BIQueryResult:
        """Answer status queries with pre-resolved entities."""
        entities_data = []
        entities_involved = []
        low_confidence_terms = []
        
        # Process resolved entities
        for query_term, entity in resolved_entities.items():
            entities_involved.append(entity)
            current_state = self.storage.get_entity_current_state(entity.id)
            
            if current_state:
                entities_data.append({
                    'query_term': query_term,
                    'entity': entity.name,
                    'type': entity.type.value,
                    'current_state': current_state,
                    'last_updated': entity.last_updated.isoformat(),
                    'confidence': entity_matches[query_term].confidence
                })

        
        # Track low confidence or unresolved terms
        for term, match in entity_matches.items():
            if not match.entity or match.confidence < 0.7:
                low_confidence_terms.append({
                    'term': term,
                    'confidence': match.confidence,
                    'match_type': match.match_type
                })
        
        # Generate answer
        if entities_data:
            answer_parts = []
            
            # Group by confidence
            high_confidence = [d for d in entities_data if d['confidence'] > 0.8]
            medium_confidence = [d for d in entities_data if 0.6 < d['confidence'] <= 0.8]
            
            for data in high_confidence:
                state = data['current_state']
                status = state.get('status', 'unknown')
                answer_parts.append(f"{data['entity']} is currently {status}")
                
                if 'progress' in state:
                    answer_parts[-1] += f" with {state['progress']} progress"
                if 'assigned_to' in state:
                    answer_parts[-1] += f", assigned to {state['assigned_to']}"
                if 'blockers' in state and state['blockers']:
                    answer_parts[-1] += f" (blocked by: {', '.join(state['blockers'])})"
            
            # Add uncertainty for medium confidence matches
            for data in medium_confidence:
                state = data['current_state']
                status = state.get('status', 'unknown')
                answer_parts.append(
                    f"I believe '{data['query_term']}' refers to {data['entity']}, "
                    f"which is currently {status}"
                )
            
            answer = ". ".join(answer_parts) + "."
            
            # Add note about unresolved terms
            if low_confidence_terms:
                unresolved = [t['term'] for t in low_confidence_terms if t['confidence'] < 0.3]
                if unresolved:
                    answer += f" I couldn't find clear matches for: {', '.join(unresolved)}."
            
            confidence = sum(d['confidence'] for d in entities_data) / len(entities_data)
        else:
            answer = "I couldn't find any entities matching your query."
            
            # Provide helpful information about what exists
            if intent.entities:
                entity_types = self.storage.get_analytics_data('entity_counts')
                if entity_types and entity_types.get('by_type'):
                    answer += " Available entity types in the system: "
                    answer += ", ".join([f"{count} {etype}s" 
                                       for etype, count in entity_types['by_type'].items()])
            
            confidence = 0.2
        
        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            supporting_data=entities_data,
            entities_involved=entities_involved,
            confidence=confidence,
            metadata={
                'resolution_stats': {k: v.match_type for k, v in entity_matches.items()},
                'low_confidence_terms': low_confidence_terms
            }
        )

    def _answer_ownership_query(self, 
                              query: str, 
                              intent: QueryIntent,
                              resolved_entities: Dict[str, Any],
                              entity_matches: Dict[str, EntityMatch]) -> BIQueryResult:
        """Answer ownership queries with pre-resolved entities."""
        ownership_data = []
        entities_involved = []
        low_confidence_terms = []
        
        # Process resolved entities
        for query_term, entity in resolved_entities.items():
            entities_involved.append(entity)
            relationships = self.storage.get_entity_relationships(entity.id)
            
            # Track confidence
            match = entity_matches[query_term]
            
            # Find ownership relationships
            for rel in relationships:
                if rel["relationship_type"] in [
                    "owns",
                    "responsible_for",
                    "assigned_to",
                ]:
                    ownership_data.append(
                        {
                            "query_term": query_term,
                            "entity": entity.name,
                            "owner": (
                                rel["from_entity"]["name"]
                                if rel["to_entity"]["id"] == entity.id
                                else rel["to_entity"]["name"]
                            ),
                            "relationship": rel["relationship_type"],
                            "since": rel["timestamp"],
                            "confidence": match.confidence
                        }
                    )
        
        # Track low confidence or unresolved terms
        for term, match in entity_matches.items():
            if not match.entity or match.confidence < 0.7:
                low_confidence_terms.append({
                    'term': term,
                    'confidence': match.confidence,
                    'match_type': match.match_type
                })
        
        # Generate answer with confidence awareness
        if ownership_data:
            answer_parts = []
            
            # Group by confidence
            high_confidence = [d for d in ownership_data if d['confidence'] > 0.8]
            medium_confidence = [d for d in ownership_data if 0.6 < d['confidence'] <= 0.8]
            
            for data in high_confidence:
                answer_parts.append(
                    f"{data['owner']} {data['relationship'].replace('_', ' ')} {data['entity']}"
                )
            
            for data in medium_confidence:
                answer_parts.append(
                    f"I believe {data['owner']} {data['relationship'].replace('_', ' ')} "
                    f"{data['entity']} (matched from '{data['query_term']}')"
                )
            
            answer = ". ".join(answer_parts) + "."
            
            # Add note about unresolved terms
            if low_confidence_terms:
                unresolved = [t['term'] for t in low_confidence_terms if t['confidence'] < 0.3]
                if unresolved:
                    answer += f" I couldn't find clear matches for: {', '.join(unresolved)}."
            
            confidence = sum(d['confidence'] for d in ownership_data) / len(ownership_data) if ownership_data else 0.8
        else:
            answer = "No ownership information found for the specified entities."
            
            # Provide helpful information
            if intent.entities:
                answer += " Please check that the entity names are correct."
            
            confidence = 0.3
        
        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            supporting_data=ownership_data,
            entities_involved=entities_involved,
            confidence=confidence,
            metadata={
                'resolution_stats': {k: v.match_type for k, v in entity_matches.items()},
                'low_confidence_terms': low_confidence_terms
            }
        )

    def _answer_timeline_query(self, 
                             query: str, 
                             intent: QueryIntent,
                             resolved_entities: Dict[str, Any],
                             entity_matches: Dict[str, EntityMatch]) -> BIQueryResult:
        """Answer timeline-related queries with pre-resolved entities."""
        timeline_data = []
        entities_involved = []
        low_confidence_terms = []

        # Process resolved entities
        for query_term, entity in resolved_entities.items():
            entities_involved.append(entity)
            timeline = self.storage.get_entity_timeline(entity.id)
            
            # Track confidence
            match = entity_matches[query_term]

            # Apply time filter if specified
            if intent.time_range:
                timeline = [
                    t
                    for t in timeline
                    if intent.time_range["start"]
                    <= datetime.fromisoformat(t["timestamp"])
                    <= intent.time_range["end"]
                ]

            # Add confidence and query term to each timeline event
            for event in timeline:
                event['query_term'] = query_term
                event['entity_name'] = entity.name
                event['confidence'] = match.confidence
                
            timeline_data.extend(timeline)

        # Track low confidence or unresolved terms
        for term, match in entity_matches.items():
            if not match.entity or match.confidence < 0.7:
                low_confidence_terms.append({
                    'term': term,
                    'confidence': match.confidence,
                    'match_type': match.match_type
                })

        # Sort by timestamp
        timeline_data.sort(key=lambda x: x["timestamp"], reverse=True)

        # Generate answer with confidence awareness
        if timeline_data:
            answer_parts = []
            
            # Show top 5 changes with confidence awareness
            for event in timeline_data[:5]:
                changed = ", ".join(event["changed_fields"])
                
                if event['confidence'] > 0.8:
                    answer_parts.append(
                        f"In {event['meeting_title']}, {event['entity_name']}'s {changed} changed"
                    )
                else:
                    answer_parts.append(
                        f"In {event['meeting_title']}, "
                        f"'{event['query_term']}' (matched to {event['entity_name']}) "
                        f"had {changed} changed"
                    )
                    
                if event["reason"]:
                    answer_parts[-1] += f" because {event['reason']}"

            answer = ". ".join(answer_parts) + "."
            
            # Add note about unresolved terms
            if low_confidence_terms:
                unresolved = [t['term'] for t in low_confidence_terms if t['confidence'] < 0.3]
                if unresolved:
                    answer += f" I couldn't find timeline data for: {', '.join(unresolved)}."
                    
            confidence = sum(e['confidence'] for e in timeline_data[:5]) / min(5, len(timeline_data)) if timeline_data else 0.8
        else:
            answer = "No timeline data found for the specified entities."
            
            # Provide helpful information
            if intent.entities:
                answer += " Please check that the entity names are correct."
                
            confidence = 0.3

        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            supporting_data=timeline_data,
            entities_involved=entities_involved,
            confidence=confidence,
            metadata={
                'resolution_stats': {k: v.match_type for k, v in entity_matches.items()},
                'low_confidence_terms': low_confidence_terms
            }
        )

    def _answer_relationship_query(
        self, 
        query: str, 
        intent: QueryIntent,
        resolved_entities: Dict[str, Any],
        entity_matches: Dict[str, EntityMatch]
    ) -> BIQueryResult:
        """Answer relationship queries with pre-resolved entities."""
        relationship_data = []
        entities_involved = []
        low_confidence_terms = []

        # Process resolved entities
        for query_term, entity in resolved_entities.items():
            entities_involved.append(entity)
            relationships = self.storage.get_entity_relationships(entity.id)
            
            # Track confidence
            match = entity_matches[query_term]

            # Filter by relationship type if specified
            if intent.filters.get("relationship_type"):
                relationships = [
                    r
                    for r in relationships
                    if r["relationship_type"] == intent.filters["relationship_type"]
                ]

            # Add confidence and query term to each relationship
            for rel in relationships:
                rel['query_term'] = query_term
                rel['query_entity_name'] = entity.name
                rel['confidence'] = match.confidence
                
            relationship_data.extend(relationships)

        # Track low confidence or unresolved terms
        for term, match in entity_matches.items():
            if not match.entity or match.confidence < 0.7:
                low_confidence_terms.append({
                    'term': term,
                    'confidence': match.confidence,
                    'match_type': match.match_type
                })

        # Generate answer with confidence awareness
        if relationship_data:
            answer_parts = []
            
            # Group by confidence
            high_confidence = [r for r in relationship_data[:10] if r['confidence'] > 0.8]
            medium_confidence = [r for r in relationship_data[:10] if 0.6 < r['confidence'] <= 0.8]
            
            for rel in high_confidence:
                answer_parts.append(
                    f"{rel['from_entity']['name']} {rel['relationship_type'].replace('_', ' ')} {rel['to_entity']['name']}"
                )
                
            for rel in medium_confidence:
                # Show the query term for medium confidence matches
                if rel['from_entity']['name'] == rel['query_entity_name']:
                    answer_parts.append(
                        f"'{rel['query_term']}' (matched to {rel['from_entity']['name']}) "
                        f"{rel['relationship_type'].replace('_', ' ')} {rel['to_entity']['name']}"
                    )
                else:
                    answer_parts.append(
                        f"{rel['from_entity']['name']} {rel['relationship_type'].replace('_', ' ')} "
                        f"'{rel['query_term']}' (matched to {rel['to_entity']['name']})"
                    )

            answer = ". ".join(answer_parts) + "."
            
            # Add note about unresolved terms
            if low_confidence_terms:
                unresolved = [t['term'] for t in low_confidence_terms if t['confidence'] < 0.3]
                if unresolved:
                    answer += f" I couldn't find relationships for: {', '.join(unresolved)}."
                    
            # Calculate overall confidence
            shown_relationships = relationship_data[:10]
            confidence = sum(r['confidence'] for r in shown_relationships) / len(shown_relationships) if shown_relationships else 0.8
        else:
            answer = "No relationships found for the specified entities."
            
            # Provide helpful information
            if intent.entities:
                answer += " Please check that the entity names are correct."
                
            confidence = 0.3

        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            supporting_data=relationship_data,
            entities_involved=entities_involved,
            confidence=confidence,
            metadata={
                'resolution_stats': {k: v.match_type for k, v in entity_matches.items()},
                'low_confidence_terms': low_confidence_terms
            }
        )

    def _answer_analytics_query(self, 
                              query: str, 
                              intent: QueryIntent,
                              resolved_entities: Dict[str, Any],
                              entity_matches: Dict[str, EntityMatch]) -> BIQueryResult:
        """Answer analytics queries with metadata support."""
        # Determine what metric to calculate
        metric = "entity_counts"  # Default
        if "state" in query.lower() or "change" in query.lower():
            metric = "state_changes"
        elif "relationship" in query.lower():
            metric = "relationship_network"

        analytics = self.storage.get_analytics_data(metric, intent.time_range)

        # Generate answer
        if analytics:
            if metric == "entity_counts":
                answer_parts = []
                for entity_type, count in analytics["by_type"].items():
                    answer_parts.append(f"{count} {entity_type}s")
                answer = f"System contains: {', '.join(answer_parts)}."
            elif metric == "state_changes":
                total_changes = sum(analytics["by_date"].values())
                answer = f"There have been {total_changes} state changes"
                if intent.time_range:
                    answer += " in the specified time range"
                answer += "."
            else:
                total_rels = sum(analytics["by_relationship"].values())
                answer = f"There are {total_rels} active relationships in the system."
        else:
            answer = "No analytics data available."

        # Note: Analytics queries typically don't involve specific entities
        # But we still track any that were mentioned for consistency
        entities_involved = list(resolved_entities.values()) if resolved_entities else []

        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            supporting_data=[analytics],
            entities_involved=entities_involved,
            confidence=0.8,
            visualizations=[{"type": "bar_chart", "data": analytics}],
            metadata={
                'resolution_stats': {k: v.match_type for k, v in entity_matches.items()} if entity_matches else {},
                'metric_type': metric
            }
        )

    def _answer_search_query(self, 
                           query: str, 
                           intent: QueryIntent,
                           resolved_entities: Dict[str, Any],
                           entity_matches: Dict[str, EntityMatch]) -> BIQueryResult:
        """Answer general search queries using semantic search with pre-resolved entities."""
        # Generate query embedding
        query_embedding = self.embeddings.encode(query)

        # Ensure embedding is 1D
        if query_embedding.ndim > 1:
            query_embedding = query_embedding[0]

        # Search with entity filter if entities were resolved
        filters = {}
        low_confidence_terms = []
        
        if resolved_entities:
            # Use resolved entity IDs for filtering
            entity_ids = [entity.id for entity in resolved_entities.values()]
            if entity_ids:
                filters["entity_mentions"] = entity_ids
                
        # Track low confidence or unresolved terms
        for term, match in entity_matches.items():
            if not match.entity or match.confidence < 0.7:
                low_confidence_terms.append({
                    'term': term,
                    'confidence': match.confidence,
                    'match_type': match.match_type
                })

        # Search memories
        results = self.storage.search(query_embedding, limit=5, filters=filters)

        # Build answer from results
        if results:
            answer_parts = []
            entities_involved = []

            for result in results:
                content = result.memory.content
                if result.memory.speaker:
                    answer_parts.append(f"• {result.memory.speaker}: {content}")
                else:
                    answer_parts.append(f"• {content}")

                entities_involved.extend(result.relevant_entities)

            answer = "Based on meeting discussions:\n" + "\n".join(answer_parts)
            
            # Add note about entity filters used
            if resolved_entities:
                resolved_names = [e.name for e in resolved_entities.values()]
                answer += f"\n\n(Filtered by entities: {', '.join(resolved_names)})"
                
            # Add note about unresolved terms
            if low_confidence_terms:
                unresolved = [t['term'] for t in low_confidence_terms if t['confidence'] < 0.3]
                if unresolved:
                    answer += f"\n\nNote: I couldn't find clear matches for: {', '.join(unresolved)}."

            supporting_data = [
                {
                    "content": r.memory.content,
                    "speaker": r.memory.speaker,
                    "meeting": r.meeting.title if r.meeting else "Unknown",
                    "score": r.score,
                }
                for r in results
            ]
            
            # Calculate confidence based on search results and entity resolution
            base_confidence = 0.7 if results else 0.2
            if entity_matches:
                avg_entity_confidence = sum(m.confidence for m in entity_matches.values()) / len(entity_matches)
                confidence = (base_confidence + avg_entity_confidence) / 2
            else:
                confidence = base_confidence
        else:
            answer = "No relevant information found in meeting history."
            
            # Provide more context if entities were mentioned
            if intent.entities:
                answer += " This could be because:\n"
                answer += "• The entities mentioned haven't been discussed in meetings\n"
                answer += "• The entity names might not match exactly\n"
                
                if low_confidence_terms:
                    unresolved = [t['term'] for t in low_confidence_terms]
                    answer += f"• These terms had low match confidence: {', '.join(unresolved)}"
                    
            supporting_data = []
            entities_involved = list(resolved_entities.values()) if resolved_entities else []
            confidence = 0.2

        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            supporting_data=supporting_data,
            entities_involved=entities_involved,
            confidence=confidence,
            metadata={
                'resolution_stats': {k: v.match_type for k, v in entity_matches.items()} if entity_matches else {},
                'low_confidence_terms': low_confidence_terms,
                'search_filters': filters
            }
        )

    def synthesize_answer(self, query: str, context: List[Dict[str, Any]]) -> str:
        """Use LLM to synthesize a natural language answer from context."""
        context_str = json.dumps(context, indent=2)

        try:
            response = self.client.chat.completions.create(
                model=settings.openrouter_model,
                messages=[
                    {
                        "role": "system",
                        "content": "Generate a clear, concise answer to the user's question based on the provided context.",
                    },
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nContext:\n{context_str}\n\nAnswer:",
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to synthesize answer: {e}")
            return "I am sorry, but I encountered an error while trying to synthesize an answer from the available data."
