"""
Production-ready Query Engine with temporal support and comprehensive BI features.
Handles ALL query types with intelligent fallbacks.
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from src.models import (
    Entity, EntityState, StateTransition, Memory,
    QueryIntent, BIQueryResult, SearchResult
)
from src.storage import MemoryStorage as Storage
from src.embeddings import EmbeddingEngine as LocalEmbeddings
from src.entity_resolver import EntityResolver
from openai import OpenAI
from src.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryContext:
    """Enhanced context for query processing"""
    query: str
    intent: QueryIntent
    entities: List[Entity]
    memories: List[SearchResult]
    state_history: Dict[str, List[EntityState]]
    transitions: Dict[str, List[StateTransition]]
    relationships: Dict[str, List[Dict]]
    metadata: Dict[str, Any]


class ProductionQueryEngine:
    """Production-ready query engine with comprehensive BI support."""
    
    # Intent patterns with scoring weights
    INTENT_PATTERNS = {
        "timeline": {
            "patterns": [
                r"how did .* (?:progress|evolve|change)",
                r"timeline (?:for|of)",
                r"evolution of",
                r"history of",
                r"changes over time",
                r"show (?:me )?(?:the )?progress",
                r"track(?:ing)? .* over time"
            ],
            "score_weight": 0.9,
            "keywords": ["timeline", "history", "evolution", "progress", "changes"]
        },
        "blocker": {
            "patterns": [
                r"what(?:'s| is| are) (?:blocking|blocked)",
                r"blockers? (?:for|on|in)",
                r"what's blocked",
                r"waiting on",
                r"stuck on",
                r"impediments?",
                r"obstacles?"
            ],
            "score_weight": 0.85,
            "keywords": ["blocker", "blocked", "blocking", "waiting", "stuck", "impediment"]
        },
        "status": {
            "patterns": [
                r"(?:current |latest )?status (?:of|for)",
                r"where (?:is|are)",
                r"what(?:'s| is) the status",
                r"progress on",
                r"how (?:is|are) .* doing",
                r"update on"
            ],
            "score_weight": 0.8,
            "keywords": ["status", "current", "latest", "progress", "update"]
        },
        "ownership": {
            "patterns": [
                r"who (?:owns|is owner)",
                r"who(?:'s| is) (?:responsible|working|leading)",
                r"assigned to",
                r"ownership of",
                r"team (?:for|on|working)"
            ],
            "score_weight": 0.8,
            "keywords": ["owner", "owns", "responsible", "assigned", "team", "lead"]
        },
        "analytics": {
            "patterns": [
                r"how many",
                r"count of",
                r"metrics? (?:for|on)",
                r"analytics? (?:for|on)",
                r"statistics?",
                r"breakdown of",
                r"distribution"
            ],
            "score_weight": 0.75,
            "keywords": ["metrics", "analytics", "count", "statistics", "breakdown"]
        },
        "relationship": {
            "patterns": [
                r"(?:dependencies|depends) (?:on|for)",
                r"related to",
                r"connected to",
                r"impacts? on",
                r"affected by"
            ],
            "score_weight": 0.75,
            "keywords": ["dependencies", "related", "connected", "impacts", "affects"]
        },
        "search": {
            "patterns": [
                r"find (?:all )?(?:mentions|references)",
                r"search for",
                r"look for",
                r"where .* mentioned",
                r"discussions? (?:about|on)"
            ],
            "score_weight": 0.7,
            "keywords": ["find", "search", "mentions", "references", "discussions"]
        }
    }
    
    def __init__(self, storage: Storage, embeddings: LocalEmbeddings, entity_resolver: EntityResolver, llm_client: OpenAI):
        self.storage = storage
        self.embeddings = embeddings
        self.entity_resolver = entity_resolver
        self.llm_client = llm_client
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        for intent_type, config in self.INTENT_PATTERNS.items():
            config["compiled_patterns"] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in config["patterns"]
            ]
    
    def process_query(self, query: str, user_context: Optional[Dict] = None) -> BIQueryResult:
        """
        Process any query with intelligent routing and comprehensive results.
        This is the main entry point for all queries.
        """
        logger.info(f"Processing query: {query}")
        
        # 1. Classify intent with confidence scoring
        intent = self._classify_intent_with_confidence(query)
        logger.info(f"Classified intent: {intent.intent_type} (entities: {intent.entities})")
        
        # 2. Extract entities and context
        context = self._build_query_context(query, intent)
        
        # 3. Route to appropriate handler
        if intent.intent_type == "timeline":
            result = self._handle_timeline_query(context)
        elif intent.intent_type == "blocker":
            result = self._handle_blocker_query(context)
        elif intent.intent_type == "status":
            result = self._handle_status_query(context)
        elif intent.intent_type == "ownership":
            result = self._handle_ownership_query(context)
        elif intent.intent_type == "analytics":
            result = self._handle_analytics_query(context)
        elif intent.intent_type == "relationship":
            result = self._handle_relationship_query(context)
        else:
            result = self._handle_search_query(context)
        
        # 4. Enhance with follow-up suggestions
        result.metadata = result.metadata or {}
        result.metadata["follow_up_suggestions"] = self._generate_follow_up_suggestions(context, result)
        
        return result
    
    def _classify_intent_with_confidence(self, query: str) -> QueryIntent:
        """Classify query intent with confidence scoring."""
        query_lower = query.lower()
        scores = defaultdict(float)
        
        # Score based on patterns
        for intent_type, config in self.INTENT_PATTERNS.items():
            for pattern in config["compiled_patterns"]:
                if pattern.search(query):
                    scores[intent_type] += config["score_weight"]
            
            # Keyword scoring
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    scores[intent_type] += 0.3
        
        # Extract entities mentioned in query
        entities = self._extract_query_entities(query)
        
        # Determine best intent
        if scores:
            best_intent = max(scores.items(), key=lambda x: x[1])
            intent_type = best_intent[0]
            confidence = min(best_intent[1], 1.0)
        else:
            intent_type = "search"
            confidence = 0.5
        
        # Build filters based on query
        filters = self._extract_query_filters(query)
        
        return QueryIntent(
            intent_type=intent_type,
            entities=entities,
            filters=filters,
            time_range=self._extract_time_range(query),
            aggregation=self._extract_aggregation_type(query)
        )
    
    def _extract_query_entities(self, query: str) -> List[str]:
        """Extract entity names mentioned in the query."""
        entities = []
        
        # Get all known entities
        all_entities = self.storage.get_all_entities()
        
        # Check for entity mentions
        query_lower = query.lower()
        for entity in all_entities:
            if entity.name.lower() in query_lower:
                entities.append(entity.name)
            elif entity.normalized_name in query_lower:
                entities.append(entity.name)
        
        return entities
    
    def _extract_time_range(self, query: str) -> Optional[Dict[str, datetime]]:
        """Extract time range from query."""
        now = datetime.now()
        query_lower = query.lower()
        
        # Time range patterns
        if "today" in query_lower:
            return {
                "start": now.replace(hour=0, minute=0, second=0),
                "end": now
            }
        elif "yesterday" in query_lower:
            yesterday = now - timedelta(days=1)
            return {
                "start": yesterday.replace(hour=0, minute=0, second=0),
                "end": yesterday.replace(hour=23, minute=59, second=59)
            }
        elif "this week" in query_lower:
            start = now - timedelta(days=now.weekday())
            return {
                "start": start.replace(hour=0, minute=0, second=0),
                "end": now
            }
        elif "last week" in query_lower:
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            return {
                "start": start.replace(hour=0, minute=0, second=0),
                "end": end.replace(hour=23, minute=59, second=59)
            }
        elif re.search(r"(?:last|past) (\d+) days?", query_lower):
            match = re.search(r"(?:last|past) (\d+) days?", query_lower)
            days = int(match.group(1))
            return {
                "start": now - timedelta(days=days),
                "end": now
            }
        
        # Check for Q1, Q2, etc.
        quarter_match = re.search(r"Q(\d) (?:(\d{4})|(?:of )?this year)?", query, re.IGNORECASE)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            year = int(quarter_match.group(2)) if quarter_match.group(2) else now.year
            
            quarter_starts = {
                1: datetime(year, 1, 1),
                2: datetime(year, 4, 1),
                3: datetime(year, 7, 1),
                4: datetime(year, 10, 1)
            }
            
            if quarter in quarter_starts:
                start = quarter_starts[quarter]
                if quarter < 4:
                    end = quarter_starts[quarter + 1] - timedelta(days=1)
                else:
                    end = datetime(year, 12, 31)
                
                return {"start": start, "end": end}
        
        return None
    
    def _build_query_context(self, query: str, intent: QueryIntent) -> QueryContext:
        """Build comprehensive context for query processing."""
        context = QueryContext(
            query=query,
            intent=intent,
            entities=[],
            memories=[],
            state_history={},
            transitions={},
            relationships={},
            metadata={}
        )
        
        # Load entities
        if intent.entities:
            for entity_name in intent.entities:
                entity = self.storage.get_entity_by_name(entity_name)
                if entity:
                    context.entities.append(entity)
                    
                    # Load state history
                    states = self.storage.get_entity_timeline(entity.id)
                    context.state_history[entity.id] = states
                    
                    # Load transitions (timeline returns dicts, not StateTransition objects)
                    timeline_data = self.storage.get_entity_timeline(entity.id)
                    # Convert dicts to StateTransition-like objects for compatibility
                    transitions = []
                    for item in timeline_data:
                        transitions.append(type('Transition', (), {
                            'timestamp': datetime.fromisoformat(item['timestamp']),
                            'from_state': item['from_state'],
                            'to_state': item['to_state'],
                            'changed_fields': item['changed_fields'],
                            'reason': item['reason'],
                            'meeting_id': item['meeting_id']
                        })())
                    context.transitions[entity.id] = transitions
                    
                    # Load relationships
                    relationships = self.storage.get_entity_relationships(entity.id)
                    context.relationships[entity.id] = relationships
        
        # Semantic search for relevant memories
        if query:
            search_results = self._search_memories(query, limit=20)
            context.memories = search_results
        
        return context
    
    def _handle_timeline_query(self, context: QueryContext) -> BIQueryResult:
        """Handle timeline queries with comprehensive history."""
        timelines = []
        
        for entity in context.entities:
            timeline_data = {
                "entity": entity.name,
                "type": entity.type.value,
                "timeline": []
            }
            
            # Get transitions or reconstruct from states
            transitions = context.transitions.get(entity.id, [])
            
            if not transitions:
                # Reconstruct from states
                transitions = self._reconstruct_transitions_from_states(
                    entity.id, 
                    context.state_history.get(entity.id, [])
                )
            
            # Format timeline entries
            for transition in transitions:
                entry = {
                    "date": transition.timestamp.isoformat(),
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "changes": transition.changed_fields,
                    "reason": transition.reason
                }
                timeline_data["timeline"].append(entry)
            
            timelines.append(timeline_data)
        
        # Generate comprehensive response
        response = self._generate_timeline_response(timelines, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=timelines,
            entities_involved=context.entities,
            confidence=response["confidence"],
            visualizations=self._create_timeline_visualizations(timelines),
            metadata={"timeline_count": len(timelines)}
        )
    
    def _handle_blocker_query(self, context: QueryContext) -> BIQueryResult:
        """Handle blocker queries with resolution tracking."""
        blockers = []
        
        # Search for blocked entities
        if context.intent.time_range:
            # Time-bounded search
            start = context.intent.time_range["start"]
            end = context.intent.time_range["end"]
            
            # Get all entities and filter by state
            all_entities = self.storage.get_all_entities()
            blocked_entities = self._filter_entities_by_state(
                state_filter={"status": "blocked"},
                entities=all_entities
            )
        else:
            # Current blockers
            blocked_entities = self._filter_entities_by_state(
                state_filter={"status": "blocked"}
            )
        
        # Build blocker details
        for entity in blocked_entities:
            blocker_info = {
                "entity": entity.name,
                "type": entity.type.value,
                "current_blockers": [],
                "resolution_history": []
            }
            
            # Get current state
            current_states = self.storage.get_entity_current_state(entity.id)
            if current_states:
                state = current_states[0].state
                if isinstance(state, str):
                    import json
                    state = json.loads(state)
                
                if state.get("blockers"):
                    blocker_info["current_blockers"] = state["blockers"]
            
            # Get blocker resolution history
            transitions = self.storage.get_entity_timeline(entity.id)
            for transition in transitions:
                if "blockers" in transition.changed_fields:
                    blocker_info["resolution_history"].append({
                        "date": transition.timestamp.isoformat(),
                        "change": transition.reason,
                        "from_blockers": transition.from_state.get("blockers", []) if transition.from_state else [],
                        "to_blockers": transition.to_state.get("blockers", [])
                    })
            
            blockers.append(blocker_info)
        
        # Generate response
        response = self._generate_blocker_response(blockers, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=blockers,
            entities_involved=blocked_entities,
            confidence=response["confidence"],
            metadata={"blocker_count": len(blockers)}
        )
    
    def _handle_status_query(self, context: QueryContext) -> BIQueryResult:
        """Handle status queries with current state information."""
        status_data = []
        
        for entity in context.entities:
            entity_status = {
                "entity": entity.name,
                "type": entity.type.value,
                "current_state": {},
                "last_updated": None,
                "recent_changes": []
            }
            
            # Get current state
            current_states = self.storage.get_entity_current_state(entity.id)
            if current_states:
                state = current_states[0]
                entity_status["current_state"] = state.state if isinstance(state.state, dict) else json.loads(state.state)
                entity_status["last_updated"] = state.timestamp.isoformat()
            
            # Get recent changes
            transitions = context.transitions.get(entity.id, [])
            recent_transitions = sorted(transitions, key=lambda t: t.timestamp, reverse=True)[:3]
            
            for transition in recent_transitions:
                entity_status["recent_changes"].append({
                    "date": transition.timestamp.isoformat(),
                    "change": transition.reason,
                    "fields": transition.changed_fields
                })
            
            status_data.append(entity_status)
        
        # Generate response
        response = self._generate_status_response(status_data, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=status_data,
            entities_involved=context.entities,
            confidence=response["confidence"],
            metadata={"entity_count": len(status_data)}
        )
    
    def _reconstruct_transitions_from_states(self, entity_id: str, states: List[EntityState]) -> List[StateTransition]:
        """Reconstruct transitions from state history when not available."""
        transitions = []
        
        if len(states) < 2:
            return transitions
        
        # Sort by timestamp
        sorted_states = sorted(states, key=lambda s: s.timestamp)
        
        for i in range(1, len(sorted_states)):
            prev_state = sorted_states[i-1]
            curr_state = sorted_states[i]
            
            # Parse states
            prev_data = prev_state.state if isinstance(prev_state.state, dict) else json.loads(prev_state.state)
            curr_data = curr_state.state if isinstance(curr_state.state, dict) else json.loads(curr_state.state)
            
            # Detect changes
            changed_fields = []
            for key in set(list(prev_data.keys()) + list(curr_data.keys())):
                if prev_data.get(key) != curr_data.get(key):
                    changed_fields.append(key)
            
            if changed_fields:
                transition = StateTransition(
                    entity_id=entity_id,
                    from_state=prev_data,
                    to_state=curr_data,
                    changed_fields=changed_fields,
                    reason="Reconstructed from state history",
                    meeting_id=curr_state.meeting_id,
                    timestamp=curr_state.timestamp
                )
                transitions.append(transition)
        
        return transitions
    
    def _generate_timeline_response(self, timelines: List[Dict], context: QueryContext) -> Dict[str, Any]:
        """Generate natural language response for timeline queries."""
        
        prompt = f"""
Based on the timeline data below, provide a comprehensive answer to this query: {context.query}

Timeline Data:
{json.dumps(timelines, indent=2)}

Instructions:
1. Describe the progression chronologically
2. Highlight key state changes and milestones
3. Note any patterns or significant events
4. If multiple entities, compare their progressions
5. Be specific about dates and changes

Format the response in clear, business-friendly language.

You MUST respond with valid JSON in this exact format:
{
    "answer": "Your comprehensive answer here",
    "confidence": 0.95
}
"""
        
        json_schema = {
            "name": "timeline_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": { "type": "string", "description": "A comprehensive answer to the user's query based on the timeline data." },
                    "confidence": { "type": "number", "description": "Confidence score in the answer, from 0.0 to 1.0." }
                },
                "required": ["answer", "confidence"]
            }
        }

        # Use OpenAI client with strict JSON mode
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes timeline data and provides comprehensive answers. Respond only with valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000,
        )
        
        response_text = response.choices[0].message.content
        response_json = json.loads(response_text)
        
        return response_json

    def _search_memories(self, query: str, limit: int = 20) -> List[SearchResult]:
        """Search memories using vector similarity."""
        # Generate embedding for query
        query_embedding = self.embeddings.encode([query])[0]
        
        # Search in Qdrant
        results = self.storage.search_memories(
            query_embedding=query_embedding,
            limit=limit
        )
        
        return results
    
    def _generate_follow_up_suggestions(self, context: QueryContext, result: BIQueryResult) -> List[str]:
        """Generate intelligent follow-up query suggestions."""
        suggestions = []
        
        if context.intent.intent_type == "timeline":
            for entity in context.entities:
                suggestions.append(f"What factors influenced {entity.name}'s progress?")
                suggestions.append(f"Who was involved in {entity.name} at each stage?")
        
        elif context.intent.intent_type == "blocker":
            suggestions.append("What patterns do we see in blockers?")
            suggestions.append("Which teams or projects have the most blockers?")
            suggestions.append("How long do blockers typically last?")
        
        elif context.intent.intent_type == "status":
            for entity in context.entities:
                suggestions.append(f"What's the timeline for {entity.name}?")
                suggestions.append(f"What are the dependencies for {entity.name}?")
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _create_timeline_visualizations(self, timelines: List[Dict]) -> List[Dict[str, Any]]:
        """Create visualization data for timelines."""
        visualizations = []
        
        for timeline_data in timelines:
            viz = {
                "type": "timeline",
                "entity": timeline_data["entity"],
                "data": []
            }
            
            for entry in timeline_data["timeline"]:
                viz["data"].append({
                    "x": entry["date"],
                    "y": entry["to_state"].get("status", "unknown"),
                    "label": entry["reason"]
                })
            
            visualizations.append(viz)
        
        return visualizations
    
    def _generate_blocker_response(self, blockers: List[Dict], context: QueryContext) -> Dict[str, Any]:
        """Generate response for blocker queries."""
        prompt = f"""
Based on the blocker data below, answer this query: {context.query}

Blocker Data:
{json.dumps(blockers, indent=2)}

Instructions:
1. List all current blockers clearly
2. Group by severity or impact if applicable
3. Show resolution history for resolved blockers
4. Identify any patterns or recurring issues
5. Suggest potential resolution paths

Be specific and actionable in your response.

You MUST respond with valid JSON in this exact format:
{
    "answer": "Your comprehensive answer here",
    "confidence": 0.95
}
"""
        
        json_schema = {
            "name": "blocker_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": { "type": "string", "description": "A comprehensive answer to the user's query based on the blocker data." },
                    "confidence": { "type": "number", "description": "Confidence score in the answer, from 0.0 to 1.0." }
                },
                "required": ["answer", "confidence"]
            }
        }

        # Use OpenAI client with strict JSON mode
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes blocker data and provides comprehensive answers. Respond only with valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800,
        )
        
        response_text = response.choices[0].message.content
        response_json = json.loads(response_text)
        
        return response_json
    
    def _generate_status_response(self, status_data: List[Dict], context: QueryContext) -> Dict[str, Any]:
        """Generate response for status queries."""
        prompt = f"""
Based on the status data below, answer this query: {context.query}

Status Data:
{json.dumps(status_data, indent=2)}

Instructions:
1. Provide current status for each entity
2. Highlight any critical information (blockers, delays)
3. Note recent changes or updates
4. Include relevant metrics (progress %, dates)
5. Be concise but comprehensive

Format as a clear status update.

You MUST respond with valid JSON in this exact format:
{
    "answer": "Your comprehensive answer here",
    "confidence": 0.95
}
"""
        
        json_schema = {
            "name": "status_response",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "answer": { "type": "string", "description": "A comprehensive answer to the user's query based on the status data." },
                    "confidence": { "type": "number", "description": "Confidence score in the answer, from 0.0 to 1.0." }
                },
                "required": ["answer", "confidence"]
            }
        }

        # Use OpenAI client with strict JSON mode
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes status data and provides comprehensive answers. Respond only with valid JSON matching the requested schema."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=600,
        )
        
        response_text = response.choices[0].message.content
        response_json = json.loads(response_text)
        
        return response_json
    
    def _extract_query_filters(self, query: str) -> Dict[str, Any]:
        """Extract filters from query text."""
        filters = {}
        query_lower = query.lower()
        
        # Status filters
        if "in progress" in query_lower:
            filters["status"] = "in_progress"
        elif "blocked" in query_lower:
            filters["status"] = "blocked"
        elif "completed" in query_lower:
            filters["status"] = "completed"
        elif "planned" in query_lower:
            filters["status"] = "planned"
        
        # Type filters
        if "project" in query_lower:
            filters["type"] = "project"
        elif "feature" in query_lower:
            filters["type"] = "feature"
        elif "task" in query_lower:
            filters["type"] = "task"
        
        return filters
    
    def _extract_aggregation_type(self, query: str) -> Optional[str]:
        """Extract aggregation type from query."""
        query_lower = query.lower()
        
        if "count" in query_lower or "how many" in query_lower:
            return "count"
        elif "average" in query_lower or "avg" in query_lower:
            return "average"
        elif "sum" in query_lower or "total" in query_lower:
            return "sum"
        elif "group by" in query_lower:
            return "group"
        
        return None
    
    def _filter_entities_by_state(self, state_filter: Dict[str, Any], entities: Optional[List[Entity]] = None) -> List[Entity]:
        """Filter entities by their current state."""
        if entities is None:
            entities = self.storage.get_all_entities()
        
        filtered = []
        for entity in entities:
            current_state = self.storage.get_entity_current_state(entity.id)
            if current_state:
                # Check if state matches filter
                match = True
                for key, value in state_filter.items():
                    if key == "$exists":
                        # Handle existence checks
                        continue
                    state_value = current_state.get(key)
                    if isinstance(value, dict) and "$exists" in value:
                        # Check if field exists
                        if value["$exists"] and state_value is None:
                            match = False
                            break
                        elif not value["$exists"] and state_value is not None:
                            match = False
                            break
                    elif state_value != value:
                        match = False
                        break
                if match:
                    filtered.append(entity)
        
        return filtered
    
    def _handle_ownership_query(self, context: QueryContext) -> BIQueryResult:
        """Handle ownership and assignment queries."""
        ownership_data = []
        
        # Get all entities with ownership info
        if context.entities:
            entities_to_check = context.entities
        else:
            # Search all entities with ownership info
            entities_to_check = self._filter_entities_by_state(
                state_filter={"assigned_to": {"$exists": True}}
            )
        
        for entity in entities_to_check:
            ownership_info = {
                "entity": entity.name,
                "type": entity.type.value,
                "current_owner": None,
                "ownership_history": []
            }
            
            # Get current owner
            current_states = self.storage.get_entity_current_state(entity.id)
            if current_states:
                state = current_states[0].state
                if isinstance(state, str):
                    state = json.loads(state)
                ownership_info["current_owner"] = state.get("assigned_to")
            
            # Get ownership history
            transitions = self.storage.get_entity_timeline(entity.id)
            for transition in transitions:
                if "assigned_to" in transition.changed_fields:
                    ownership_info["ownership_history"].append({
                        "date": transition.timestamp.isoformat(),
                        "from": transition.from_state.get("assigned_to") if transition.from_state else None,
                        "to": transition.to_state.get("assigned_to"),
                        "reason": transition.reason
                    })
            
            ownership_data.append(ownership_info)
        
        # Generate response
        response = self._generate_ownership_response(ownership_data, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=ownership_data,
            entities_involved=entities_to_check,
            confidence=response["confidence"],
            metadata={"ownership_count": len(ownership_data)}
        )
    
    def _handle_analytics_query(self, context: QueryContext) -> BIQueryResult:
        """Handle analytics and metrics queries."""
        analytics_data = {}
        
        # Determine what metrics to calculate
        if context.intent.aggregation == "count":
            analytics_data = self._calculate_counts(context)
        else:
            analytics_data = self._calculate_comprehensive_metrics(context)
        
        # Generate response
        response = self._generate_analytics_response(analytics_data, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=[analytics_data],
            entities_involved=context.entities,
            confidence=response["confidence"],
            visualizations=self._create_analytics_visualizations(analytics_data),
            metadata=analytics_data
        )
    
    def _handle_relationship_query(self, context: QueryContext) -> BIQueryResult:
        """Handle dependency and relationship queries."""
        relationship_data = []
        
        for entity in context.entities:
            rel_info = {
                "entity": entity.name,
                "type": entity.type.value,
                "relationships": {
                    "depends_on": [],
                    "blocks": [],
                    "works_with": [],
                    "owns": []
                }
            }
            
            # Get all relationships
            relationships = context.relationships.get(entity.id, [])
            
            for rel in relationships:
                rel_type = rel["relationship_type"]
                if rel_type in rel_info["relationships"]:
                    rel_info["relationships"][rel_type].append({
                        "entity": rel["to_entity"]["name"],
                        "type": rel["to_entity"]["type"],
                        "since": rel["timestamp"]
                    })
            
            relationship_data.append(rel_info)
        
        # Generate response
        response = self._generate_relationship_response(relationship_data, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=relationship_data,
            entities_involved=context.entities,
            confidence=response["confidence"],
            metadata={"relationship_count": sum(len(r["relationships"]) for r in relationship_data)}
        )
    
    def _handle_search_query(self, context: QueryContext) -> BIQueryResult:
        """Handle general search queries."""
        # Use semantic search
        search_results = context.memories[:10]  # Top 10 results
        
        # Extract relevant information
        relevant_data = []
        for result in search_results:
            relevant_data.append({
                "content": result.memory.content,
                "meeting": result.meeting.title if result.meeting else "Unknown",
                "date": result.meeting.date.isoformat() if result.meeting else None,
                "score": result.score,
                "entities": [e.name for e in result.relevant_entities]
            })
        
        # Generate response
        response = self._generate_search_response(relevant_data, context)
        
        return BIQueryResult(
            query=context.query,
            intent=context.intent,
            answer=response["answer"],
            supporting_data=relevant_data,
            entities_involved=[e for r in search_results for e in r.relevant_entities],
            confidence=response["confidence"],
            metadata={"result_count": len(relevant_data)}
        )
    
    def _calculate_counts(self, context: QueryContext) -> Dict[str, Any]:
        """Calculate count-based metrics."""
        counts = {
            "total_entities": 0,
            "by_type": defaultdict(int),
            "by_status": defaultdict(int),
            "blocked_count": 0,
            "completed_count": 0,
            "in_progress_count": 0
        }
        
        # Get all entities or filtered set
        if context.intent.filters:
            entities = self._filter_entities_by_state(
                state_filter=context.intent.filters
            )
            # TODO: Add time range filtering
        else:
            entities = self.storage.get_all_entities()
        
        for entity in entities:
            counts["total_entities"] += 1
            counts["by_type"][entity.type.value] += 1
            
            # Get current state
            current_states = self.storage.get_entity_current_state(entity.id)
            if current_states:
                state = current_states[0].state
                if isinstance(state, str):
                    state = json.loads(state)
                
                status = state.get("status", "unknown")
                counts["by_status"][status] += 1
                
                if status == "blocked":
                    counts["blocked_count"] += 1
                elif status == "completed":
                    counts["completed_count"] += 1
                elif status == "in_progress":
                    counts["in_progress_count"] += 1
        
        return dict(counts)
    
    def _calculate_comprehensive_metrics(self, context: QueryContext) -> Dict[str, Any]:
        """Calculate comprehensive analytics metrics."""
        metrics = {
            "summary": self._calculate_counts(context),
            "velocity": self._calculate_velocity_metrics(context),
            "cycle_time": self._calculate_cycle_time_metrics(context),
            "blocker_metrics": self._calculate_blocker_metrics(context)
        }
        
        return metrics
    
    def _calculate_velocity_metrics(self, context: QueryContext) -> Dict[str, Any]:
        """Calculate velocity and throughput metrics."""
        velocity = {
            "completed_per_week": defaultdict(int),
            "started_per_week": defaultdict(int),
            "average_completion_rate": 0
        }
        
        # Get all transitions
        all_transitions = []
        for entity in self.storage.get_all_entities():
            transitions = self.storage.get_entity_timeline(entity.id)
            all_transitions.extend(transitions)
        
        # Group by week
        for transition in all_transitions:
            week = transition.timestamp.isocalendar()[1]
            
            if transition.to_state.get("status") == "completed":
                velocity["completed_per_week"][week] += 1
            elif transition.to_state.get("status") == "in_progress" and (
                not transition.from_state or transition.from_state.get("status") != "in_progress"
            ):
                velocity["started_per_week"][week] += 1
        
        # Calculate average
        if velocity["completed_per_week"]:
            velocity["average_completion_rate"] = sum(velocity["completed_per_week"].values()) / len(velocity["completed_per_week"])
        
        return dict(velocity)
    
    def _calculate_cycle_time_metrics(self, context: QueryContext) -> Dict[str, Any]:
        """Calculate cycle time metrics."""
        cycle_times = []
        
        for entity in self.storage.get_all_entities():
            transitions = self.storage.get_entity_timeline(entity.id)
            
            # Find start and end times
            start_time = None
            end_time = None
            
            for transition in transitions:
                if transition.to_state.get("status") == "in_progress" and not start_time:
                    start_time = transition.timestamp
                elif transition.to_state.get("status") == "completed":
                    end_time = transition.timestamp
            
            if start_time and end_time:
                cycle_time = (end_time - start_time).days
                cycle_times.append(cycle_time)
        
        metrics = {
            "average_cycle_time_days": sum(cycle_times) / len(cycle_times) if cycle_times else 0,
            "min_cycle_time_days": min(cycle_times) if cycle_times else 0,
            "max_cycle_time_days": max(cycle_times) if cycle_times else 0,
            "total_completed": len(cycle_times)
        }
        
        return metrics
    
    def _calculate_blocker_metrics(self, context: QueryContext) -> Dict[str, Any]:
        """Calculate blocker-related metrics."""
        blocker_durations = []
        blocker_types = defaultdict(int)
        
        for entity in self.storage.get_all_entities():
            transitions = self.storage.get_entity_timeline(entity.id)
            
            # Track blocker periods
            blocked_start = None
            
            for transition in transitions:
                if transition.to_state.get("status") == "blocked":
                    blocked_start = transition.timestamp
                    # Count blocker types
                    blockers = transition.to_state.get("blockers", [])
                    for blocker in blockers:
                        blocker_types[blocker] += 1
                        
                elif blocked_start and transition.from_state and transition.from_state.get("status") == "blocked":
                    # Blocker resolved
                    duration = (transition.timestamp - blocked_start).days
                    blocker_durations.append(duration)
                    blocked_start = None
        
        metrics = {
            "average_blocker_duration_days": sum(blocker_durations) / len(blocker_durations) if blocker_durations else 0,
            "total_blockers_resolved": len(blocker_durations),
            "most_common_blockers": dict(sorted(blocker_types.items(), key=lambda x: x[1], reverse=True)[:5])
        }
        
        return metrics
    
    def _create_analytics_visualizations(self, analytics_data: Dict) -> List[Dict[str, Any]]:
        """Create visualization data for analytics."""
        visualizations = []
        
        # Status distribution pie chart
        if "summary" in analytics_data and "by_status" in analytics_data["summary"]:
            viz = {
                "type": "pie",
                "title": "Status Distribution",
                "data": [
                    {"label": status, "value": count}
                    for status, count in analytics_data["summary"]["by_status"].items()
                ]
            }
            visualizations.append(viz)
        
        # Velocity trend line chart
        if "velocity" in analytics_data and "completed_per_week" in analytics_data["velocity"]:
            viz = {
                "type": "line",
                "title": "Weekly Completion Rate",
                "data": [
                    {"x": f"Week {week}", "y": count}
                    for week, count in sorted(analytics_data["velocity"]["completed_per_week"].items())
                ]
            }
            visualizations.append(viz)
        
        return visualizations
    
    def _generate_ownership_response(self, ownership_data: List[Dict], context: QueryContext) -> Dict[str, Any]:
        """Generate response for ownership queries."""
        prompt = f"""
Based on the ownership data below, answer this query: {context.query}

Ownership Data:
{json.dumps(ownership_data, indent=2)}

Instructions:
1. Clearly state current owners/assignees
2. Show ownership changes if relevant
3. Group by owner if multiple entities
4. Note any entities without owners
5. Be specific about names and dates

Format as a clear ownership summary.
"""
        
        # Use OpenAI client with explicit JSON request
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes ownership data. Respond with a JSON object containing 'answer' (string) and 'confidence' (number 0-1) fields."},
                {"role": "user", "content": prompt + "\n\nRespond with JSON containing 'answer' and 'confidence' fields."}
            ],
            temperature=0.3,
            max_tokens=600
        )
        
        response_text = response.choices[0].message.content
        try:
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError:
            # Fallback if response isn't valid JSON
            return {
                "answer": response_text,
                "confidence": 0.9 if ownership_data else 0.3
            }
    
    def _generate_analytics_response(self, analytics_data: Dict, context: QueryContext) -> Dict[str, Any]:
        """Generate response for analytics queries."""
        prompt = f"""
Based on the analytics data below, answer this query: {context.query}

Analytics Data:
{json.dumps(analytics_data, indent=2)}

Instructions:
1. Present key metrics clearly
2. Highlight important trends or patterns
3. Compare metrics where relevant
4. Provide context for the numbers
5. Suggest areas of concern or success

Format as a professional analytics summary.
"""
        
        # Use OpenAI client with explicit JSON request
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes analytics data. Respond with a JSON object containing 'answer' (string) and 'confidence' (number 0-1) fields."},
                {"role": "user", "content": prompt + "\n\nRespond with JSON containing 'answer' and 'confidence' fields."}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        response_text = response.choices[0].message.content
        try:
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError:
            return {
                "answer": response_text,
                "confidence": 0.85
            }
    
    def _generate_relationship_response(self, relationship_data: List[Dict], context: QueryContext) -> Dict[str, Any]:
        """Generate response for relationship queries."""
        prompt = f"""
Based on the relationship data below, answer this query: {context.query}

Relationship Data:
{json.dumps(relationship_data, indent=2)}

Instructions:
1. Show all relevant relationships clearly
2. Highlight critical dependencies
3. Note any circular dependencies
4. Group by relationship type if helpful
5. Include impact analysis where relevant

Format as a clear dependency summary.
"""
        
        # Use OpenAI client with explicit JSON request
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes relationship data. Respond with a JSON object containing 'answer' (string) and 'confidence' (number 0-1) fields."},
                {"role": "user", "content": prompt + "\n\nRespond with JSON containing 'answer' and 'confidence' fields."}
            ],
            temperature=0.3,
            max_tokens=600
        )
        
        response_text = response.choices[0].message.content
        try:
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError:
            return {
                "answer": response_text,
                "confidence": 0.85 if relationship_data else 0.4
            }
    
    def _generate_search_response(self, search_results: List[Dict], context: QueryContext) -> Dict[str, Any]:
        """Generate response for search queries."""
        prompt = f"""
Based on the search results below, answer this query: {context.query}

Search Results:
{json.dumps(search_results, indent=2)}

Instructions:
1. Synthesize information from multiple results
2. Prioritize most relevant information
3. Include context (meeting, date, speaker)
4. Note any conflicting information
5. Be comprehensive but concise

Provide a complete answer based on the search results.
"""
        
        # Use OpenAI client with explicit JSON request
        response = self.llm_client.chat.completions.create(
            model=settings.openrouter_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes search results. Respond with a JSON object containing 'answer' (string) and 'confidence' (number 0-1) fields."},
                {"role": "user", "content": prompt + "\n\nRespond with JSON containing 'answer' and 'confidence' fields."}
            ],
            temperature=0.3,
            max_tokens=800
        )
        
        response_text = response.choices[0].message.content
        try:
            response_json = json.loads(response_text)
            return response_json
        except json.JSONDecodeError:
            return {
                "answer": response_text,
                "confidence": min(0.5 + (len(search_results) * 0.05), 0.9)
            }