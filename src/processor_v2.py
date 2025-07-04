"""
Enhanced Meeting Processor with COMPLETE state tracking.
Production-ready implementation that captures ALL state changes.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import httpx

from openai import OpenAI

from src.models import (
    Entity, EntityState, StateTransition, EntityRelationship,
    Memory, ExtractionResult, EntityType, RelationshipType
)
from src.storage import MemoryStorage as Storage
from src.entity_resolver import EntityResolver
from src.embeddings import EmbeddingEngine as LocalEmbeddings
from src.llm_processor import LLMProcessor
from src.config import settings

logger = logging.getLogger(__name__)


class EnhancedMeetingProcessor:
    """Production-ready processor with comprehensive state tracking."""
    
    # State patterns for inference - DISABLED to preserve LLM accuracy
    # These regex patterns were overwriting accurate LLM-extracted states
    # STATE_PATTERNS = {
    #     "in_progress": [
    #         r"(?:is|are) (?:now |currently )?(?:in progress|underway|being worked on)",
    #         r"(?:started|beginning|commenced) (?:work on|working on)",
    #         r"(?:actively|currently) working on",
    #         r"making (?:good )?progress on",
    #         r"(?:continues|continuing) (?:to work on|with)",
    #         r"still working on"
    #     ],
    #     "completed": [
    #         r"(?:is|are) (?:now |)?(?:complete|completed|done|finished)",
    #         r"(?:successfully |)?(?:completed|finished|delivered)",
    #         r"signed off on",
    #         r"wrapped up",
    #         r"closed out",
    #         r"(?:has|have) been (?:completed|finished)"
    #     ],
    #     "blocked": [
    #         r"(?:is|are) (?:currently |)?blocked",
    #         r"waiting (?:on|for)",
    #         r"(?:need|needs|require|requires) .* before",
    #         r"can't (?:proceed|continue|move forward)",
    #         r"(?:stuck|stalled) (?:on|at)",
    #         r"pending (?:approval|review|input)"
    #     ],
    #     "planned": [
    #         r"(?:is|are) planned",
    #         r"(?:will|going to) (?:start|begin)",
    #         r"scheduled (?:for|to)",
    #         r"(?:in the|on the) (?:roadmap|pipeline)",
    #         r"upcoming",
    #         r"(?:plan|planning) to"
    #     ],
    #     "on_hold": [
    #         r"(?:is|are) on hold",
    #         r"(?:paused|suspended)",
    #         r"(?:temporarily|indefinitely) (?:stopped|halted)",
    #         r"deprioritized"
    #     ]
    # }
    
    # # Assignment patterns for ownership detection - DISABLED
    # ASSIGNMENT_PATTERNS = [
    #     (r"(\w+(?:\s+\w+)?)\s+(?:is|will be|has been)\s+(?:leading|assigned to|responsible for|working on|owns)\s+{entity}", 1),
    #     (r"{entity}\s+(?:is|will be|has been)\s+(?:led by|assigned to|owned by)\s+(\w+(?:\s+\w+)?)", 1),
    #     (r"(\w+(?:\s+\w+)?)\s+(?:reports|reported|says|mentioned).*{entity}", 1),
    #     (r"assigning\s+{entity}\s+to\s+(\w+(?:\s+\w+)?)", 1),
    #     (r"(\w+(?:\s+\w+)?)\s+(?:takes|taking|took)\s+(?:over|ownership of)\s+{entity}", 1)
    # ]
    
    # # Progress indicators - DISABLED
    # PROGRESS_PATTERNS = [
    #     (r"(\d+)%\s+(?:complete|done|finished)", lambda m: f"{m.group(1)}%"),
    #     (r"(\d+)\s+(?:percent|pct)\s+(?:complete|done)", lambda m: f"{m.group(1)}%"),
    #     (r"(?:about|approximately|roughly)\s+(\d+)%", lambda m: f"~{m.group(1)}%"),
    #     (r"(?:quarter|1/4)\s+(?:done|complete)", lambda m: "25%"),
    #     (r"(?:half|halfway|1/2)\s+(?:done|complete)", lambda m: "50%"),
    #     (r"(?:three.?quarters|3/4)\s+(?:done|complete)", lambda m: "75%"),
    #     (r"almost (?:done|complete|finished)", lambda m: "90%"),
    #     (r"nearly (?:done|complete|finished)", lambda m: "85%")
    # ]
    
    def __init__(self, storage: Storage, entity_resolver: EntityResolver, embeddings: LocalEmbeddings, llm_processor: LLMProcessor):
        self.storage = storage
        self.entity_resolver = entity_resolver
        self.embeddings = embeddings
        self.llm_processor = llm_processor
        self.validation_metrics = {}
        # Keep llm_client for transition reason generation
        # Setup proxy configuration for corporate environments
        proxies = None
        if settings.https_proxy or settings.http_proxy:
            proxies = {}
            if settings.http_proxy:
                proxies["http://"] = settings.http_proxy
            if settings.https_proxy:
                proxies["https://"] = settings.https_proxy
            logger.info(f"Using proxy configuration: {proxies}")
        
        # Create HTTP client with proxy and SSL configuration
        http_client = httpx.Client(
            verify=settings.ssl_verify,
            proxies=proxies,
            timeout=30.0
        )
        self.llm_client = OpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            http_client=http_client
        )
        
    async def process_meeting_with_context(self, extraction: ExtractionResult, meeting_id: str) -> Dict[str, Any]:
        """
        Process meeting with COMPLETE state tracking.
        This is the production-ready implementation.
        """
        logger.info(f"Processing meeting {meeting_id} with enhanced state tracking")
        
        # Reset validation metrics
        self.validation_metrics = {
            "entities_processed": 0,
            "states_captured": 0,
            "transitions_created": 0,
            "patterns_matched": 0,
            "validation_errors": []
        }
        
        # 1. Process all entities
        entity_map = self._process_entities(extraction.entities, meeting_id)
        self.validation_metrics["entities_processed"] = len(entity_map)
        
        # 2. Fetch ALL prior states
        prior_states = self._fetch_all_prior_states(entity_map)
        logger.info(f"Fetched {len(prior_states)} prior states")
        
        # 3. Extract current states from LLM output
        extracted_states = self._extract_current_states(extraction, entity_map)
        
        # 4. Infer states from patterns in transcript - DISABLED to preserve LLM accuracy
        transcript = extraction.meeting_metadata.get("transcript_context", "")
        inferred_states = {}  # Disabled regex inference to preserve LLM accuracy
        self.validation_metrics["patterns_matched"] = 0
        
        # 5. Extract progress and assignments - DISABLED to preserve LLM accuracy
        progress_updates = {}  # Disabled regex extraction
        assignments = {}  # Disabled regex extraction
        
        # 6. Merge all state information
        final_states = self._merge_state_information(
            extracted_states, inferred_states, progress_updates, assignments
        )
        self.validation_metrics["states_captured"] = len(final_states)
        
        # 7. Create transitions for ALL changes
        transitions = await self._create_comprehensive_transitions(
            prior_states, final_states, meeting_id, extraction
        )
        self.validation_metrics["transitions_created"] = len(transitions)
        
        # 8. Process relationships
        relationships = self._process_relationships(
            extraction.relationships, entity_map, meeting_id
        )
        
        # 9. Update memory mentions
        self._update_memory_mentions(extraction.memories, entity_map)
        
        # 10. Validate completeness
        self._validate_state_tracking(entity_map, final_states, transitions)
        
        logger.info(f"Processing complete: {self.validation_metrics}")
        
        return {
            "entity_map": entity_map,
            "entities": list(entity_map.values()),
            "relationships": relationships,
            "state_changes": transitions,
            "validation": self.validation_metrics
        }
    
    def _fetch_all_prior_states(self, entity_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Fetch the most recent state for ALL entities."""
        prior_states = {}
        
        for entity_name, entity_info in entity_map.items():
            entity_id = entity_info["id"]
            
            # Get the most recent state
            current_state = self.storage.get_entity_current_state(entity_id)
            if current_state:
                # The method already returns a parsed dict
                prior_states[entity_id] = current_state
                logger.debug(f"Prior state for '{entity_name}': {current_state}")
            else:
                prior_states[entity_id] = None
                logger.debug(f"No prior state for '{entity_name}'")
        
        return prior_states
    
    def _extract_current_states(self, extraction: ExtractionResult, entity_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Extract current states from LLM extraction."""
        current_states = {}
        
        # From entities in extraction
        for entity_data in extraction.entities:
            name = entity_data.get("name", "").strip()
            if name in entity_map and "current_state" in entity_data:
                entity_id = entity_map[name]["id"]
                current_states[entity_id] = entity_data["current_state"]
        
        # Note: extraction.states is always empty in current implementation
        # All state extraction happens through entity current_state field
        
        return current_states
    
    # Method disabled to preserve LLM accuracy
    # def _infer_states_from_patterns(self, transcript: str, entity_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    #     """Infer entity states using pattern matching."""
    #     inferred_states = {}
    #     
    #     if not transcript:
    #         return inferred_states
    #     
    #     # Convert transcript to lowercase for matching
    #     transcript_lower = transcript.lower()
    #     
    #     for entity_name, entity_info in entity_map.items():
    #         entity_id = entity_info["id"]
    #         entity_lower = entity_name.lower()
    #         
    #         # Check each state pattern
    #         for state, patterns in self.STATE_PATTERNS.items():
    #             for pattern in patterns:
    #                 # Create pattern with entity name
    #                 entity_pattern = pattern.replace("{entity}", re.escape(entity_lower))
    #                 
    #                 # Also check with just the entity name mentioned nearby
    #                 context_pattern = f"(?:.{{0,50}}{re.escape(entity_lower)}.{{0,50}})(?:{pattern})"
    #                 
    #                 if re.search(entity_pattern, transcript_lower) or re.search(context_pattern, transcript_lower):
    #                     if entity_id not in inferred_states:
    #                         inferred_states[entity_id] = {}
    #                     inferred_states[entity_id]["status"] = state
    #                     logger.info(f"Inferred state '{state}' for '{entity_name}' from pattern")
    #                     break
    #     
    #     return inferred_states
    
    # Method disabled to preserve LLM accuracy
    # def _extract_progress_indicators(self, transcript: str, entity_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    #     """Extract progress percentages and indicators."""
    #     progress_updates = {}
    #     
    #     if not transcript:
    #         return progress_updates
    #     
    #     for entity_name, entity_info in entity_map.items():
    #         entity_id = entity_info["id"]
    #         entity_lower = entity_name.lower()
    #         
    #         # Look for progress mentions near entity name
    #         # Search window of 100 chars before/after entity mention
    #         pattern = f"(.{{0,100}}{re.escape(entity_lower)}.{{0,100}})"
    #         matches = re.finditer(pattern, transcript.lower())
    #         
    #         for match in matches:
    #             context = match.group(1)
    #             
    #             # Check progress patterns
    #             for prog_pattern, extractor in self.PROGRESS_PATTERNS:
    #                 prog_match = re.search(prog_pattern, context)
    #                 if prog_match:
    #                     if entity_id not in progress_updates:
    #                         progress_updates[entity_id] = {}
    #                     progress_updates[entity_id]["progress"] = extractor(prog_match)
    #                     logger.info(f"Extracted progress '{extractor(prog_match)}' for '{entity_name}'")
    #                     break
    #     
    #     return progress_updates
    
    # Method disabled to preserve LLM accuracy
    # def _extract_assignments(self, transcript: str, entity_map: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    #     """Extract ownership and assignment information."""
    #     assignments = {}
    #     
    #     if not transcript:
    #         return assignments
    #     
    #     for entity_name, entity_info in entity_map.items():
    #         entity_id = entity_info["id"]
    #         entity_lower = entity_name.lower()
    #         
    #         # Check assignment patterns
    #         for pattern_template, group_idx in self.ASSIGNMENT_PATTERNS:
    #             pattern = pattern_template.format(entity=re.escape(entity_lower))
    #             match = re.search(pattern, transcript, re.IGNORECASE)
    #             
    #             if match:
    #                 assigned_to = match.group(group_idx).strip()
    #                 if entity_id not in assignments:
    #                     assignments[entity_id] = {}
    #                 assignments[entity_id]["assigned_to"] = assigned_to
    #                 logger.info(f"Extracted assignment '{assigned_to}' for '{entity_name}'")
    #                 break
    #     
    #     return assignments
    
    def _merge_state_information(self, extracted: Dict, inferred: Dict, progress: Dict, assignments: Dict) -> Dict[str, Dict[str, Any]]:
        """Merge all sources of state information intelligently."""
        merged = {}
        
        # Start with extracted states
        for entity_id, state in extracted.items():
            if not self._is_empty_state(state):
                merged[entity_id] = state.copy()
        
        # Add inferred states (only if not already present)
        for entity_id, state in inferred.items():
            if entity_id not in merged:
                merged[entity_id] = state.copy()
            else:
                # Merge specific fields
                for key, value in state.items():
                    if key not in merged[entity_id] or merged[entity_id][key] is None:
                        merged[entity_id][key] = value
        
        # Add progress updates
        for entity_id, prog_data in progress.items():
            if entity_id not in merged:
                merged[entity_id] = {}
            merged[entity_id].update(prog_data)
        
        # Add assignments
        for entity_id, assign_data in assignments.items():
            if entity_id not in merged:
                merged[entity_id] = {}
            merged[entity_id].update(assign_data)
        
        return merged
    
    async def _create_comprehensive_transitions(
        self, 
        prior_states: Dict[str, Optional[Dict]], 
        current_states: Dict[str, Dict],
        meeting_id: str,
        extraction: ExtractionResult
    ) -> List[StateTransition]:
        """Create transitions for ALL state changes using batch LLM comparison."""
        transitions = []
        new_states = []
        state_pairs_to_compare = []
        entity_id_map = []  # Track which entity each comparison belongs to
        
        # First pass: collect all state pairs that need comparison
        for entity_id, current_state in current_states.items():
            # Skip if no actual state data
            if self._is_empty_state(current_state):
                continue
                
            prior_state = prior_states.get(entity_id)
            
            if prior_state is None:
                # First state for this entity - no comparison needed
                transition = StateTransition(
                    entity_id=entity_id,
                    from_state=None,
                    to_state=current_state,
                    changed_fields=list(current_state.keys()),
                    reason="Initial state captured",
                    meeting_id=meeting_id
                )
                transitions.append(transition)
                new_states.append(EntityState(
                    entity_id=entity_id,
                    state=current_state,
                    meeting_id=meeting_id,
                    confidence=0.9
                ))
                logger.info(f"Created initial state transition for entity {entity_id}")
            else:
                # Add to batch comparison
                state_pairs_to_compare.append((prior_state, current_state))
                entity_id_map.append(entity_id)
        
        # Batch compare all state pairs
        if state_pairs_to_compare:
            logger.info(f"Comparing {len(state_pairs_to_compare)} state pairs in batch")
            
            # Use LLM processor for batch comparison
            comparison_results = await self.llm_processor.compare_states_batch(state_pairs_to_compare)
            
            # Process comparison results
            for i, result in enumerate(comparison_results):
                entity_id = entity_id_map[i]
                prior_state = state_pairs_to_compare[i][0]
                current_state = state_pairs_to_compare[i][1]
                
                if result["has_changes"]:
                    # Create transition
                    transition = StateTransition(
                        entity_id=entity_id,
                        from_state=prior_state,
                        to_state=current_state,
                        changed_fields=result["changed_fields"],
                        reason=result["reason"],
                        meeting_id=meeting_id
                    )
                    transitions.append(transition)
                    
                    # Save new state
                    new_states.append(EntityState(
                        entity_id=entity_id,
                        state=current_state,
                        meeting_id=meeting_id,
                        confidence=0.9
                    ))
                    
                    logger.info(f"Created state transition for entity {entity_id}: {result['changed_fields']}")
                else:
                    logger.debug(f"No changes detected for entity {entity_id}")
        
        # Save all new states
        if new_states:
            self.storage.save_entity_states(new_states)
            
        # Save all transitions using batch method
        if transitions:
            self.storage.save_transitions_batch(transitions)
            logger.info(f"Saved {len(transitions)} state transitions")
        
        return transitions
    
    def _detect_field_changes(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> List[str]:
        """Detect which fields changed between states.
        Note: This is now only used for validation. Actual change detection happens in batch LLM comparison.
        """
        return self._simple_field_comparison(old_state, new_state)
    
    
    def _simple_field_comparison(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> List[str]:
        """Simple exact field comparison."""
        changed = []

        # Check for added or changed fields in new_state
        for key, new_value in new_state.items():
            if key not in old_state:
                # Field is new
                changed.append(key)
            else:
                old_value = old_state[key]
                if old_value != new_value:
                    # Field value has changed
                    changed.append(key)

        # Check for removed fields from old_state
        for key in old_state:
            if key not in new_state:
                changed.append(key)

        return changed
    
    
    def _generate_transition_reason(self, from_state: Optional[Dict], to_state: Dict, extraction: ExtractionResult) -> str:
        """Generate descriptive reason for state transition using strict JSON mode."""
        
        reason_prompt = f"""
Analyze the state transition and the meeting summary to generate a concise, human-readable reason for the change.

Previous State:
{json.dumps(from_state, indent=2)}

New State:
{json.dumps(to_state, indent=2)}

Meeting Summary:
{extraction.meeting_metadata.get('summary', 'No summary available.')}

Instructions:
1. Summarize the key change (e.g., status change, new assignment, progress update).
2. Be brief and clear. If multiple things changed, focus on the most significant one.
3. Respond with a JSON object containing a "reason" field.

Example response:
{"reason": "Status changed from planned to in_progress after team started development"}
"""

        try:
            # Use strict JSON mode
            response = self.llm_client.chat.completions.create(
                model=settings.clean_openrouter_model,
                messages=[
                    {"role": "system", "content": "You are a system that analyzes state changes and provides clear, concise reasons. Always respond with valid JSON containing a 'reason' field."},
                    {"role": "user", "content": reason_prompt}
                ],
                temperature=0.1,
                max_tokens=250,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content
            response_json = json.loads(response_text)
            return response_json.get("reason", "State updated based on meeting discussion.")

        except Exception as e:
            logger.error(f"LLM call for transition reason failed: {e}")
            # Fallback to rule-based reason generation
            return self._generate_fallback_reason(from_state, to_state)

    def _generate_fallback_reason(self, from_state: Optional[Dict], to_state: Dict) -> str:
        """Fallback to generate a rule-based transition reason."""
        if from_state is None:
            status = to_state.get("status", "unknown")
            return f"Initial state captured: {status}"

        reasons = []
        if from_state.get("status") != to_state.get("status"):
            reasons.append(f"Status changed from {from_state.get('status')} to {to_state.get('status')}")
        if from_state.get("progress") != to_state.get("progress"):
            reasons.append(f"Progress updated to {to_state.get('progress')}")
        if from_state.get("assigned_to") != to_state.get("assigned_to"):
            reasons.append(f"Assigned to {to_state.get('assigned_to')}")

        old_blockers = set(from_state.get("blockers", []))
        new_blockers = set(to_state.get("blockers", []))
        if old_blockers != new_blockers:
            added = new_blockers - old_blockers
            removed = old_blockers - new_blockers
            if added:
                reasons.append(f"New blockers: {', '.join(added)}")
            if removed:
                reasons.append(f"Resolved blockers: {', '.join(removed)}")

        return "; ".join(reasons) if reasons else "State updated"
    
    def _validate_state_tracking(self, entity_map: Dict, final_states: Dict, transitions: List):
        """Validate that state tracking is complete and accurate."""
        errors = []
        
        # Check that all entities have states
        entities_without_states = []
        for entity_name, entity_info in entity_map.items():
            entity_id = entity_info["id"]
            if entity_id not in final_states:
                # Check if entity has any prior state
                prior_states = self.storage.get_entity_current_state(entity_id)
                if not prior_states:
                    entities_without_states.append(entity_name)
        
        if entities_without_states:
            error = f"Entities without any state: {', '.join(entities_without_states)}"
            errors.append(error)
            logger.warning(error)
        
        # Validate transition consistency
        for transition in transitions:
            if transition.from_state and transition.to_state:
                # Ensure changed_fields is accurate
                actual_changes = self._detect_field_changes(
                    transition.from_state, 
                    transition.to_state
                )
                if set(actual_changes) != set(transition.changed_fields):
                    error = f"Inconsistent changed_fields for transition {transition.id}"
                    errors.append(error)
                    logger.warning(error)
        
        self.validation_metrics["validation_errors"] = errors
        
        # Log summary
        logger.info(f"Validation complete: {len(errors)} errors found")
    
    def _is_empty_state(self, state: Dict[str, Any]) -> bool:
        """Check if a state dict contains only empty values."""
        if not state:
            return True
        
        for value in state.values():
            if value is not None and value != [] and value != "":
                return False
        
        return True
    
    def _process_entities(self, raw_entities: List[Dict[str, Any]], meeting_id: str) -> Dict[str, Dict[str, Any]]:
        """Process entities with production-ready logic."""
        entity_map = {}
        processed_entities = []
        
        for raw_entity in raw_entities:
            try:
                name = raw_entity.get("name", "").strip()
                entity_type = self._validate_entity_type(raw_entity.get("type", ""))
                normalized_name = self._normalize_name(name)
                
                if not name or not entity_type:
                    logger.warning(f"Skipping entity with missing name or type: {raw_entity}")
                    continue
                
                # Check for existing entity
                existing = self.storage.get_entity_by_name(normalized_name, entity_type)
                
                if existing:
                    entity = existing
                    created = False
                    
                    # Update attributes
                    new_attrs = raw_entity.get("attributes", {})
                    if new_attrs:
                        entity.attributes.update(new_attrs)
                        entity.last_updated = datetime.now()
                else:
                    # Create new entity
                    entity = Entity(
                        type=entity_type,
                        name=name,
                        normalized_name=normalized_name,
                        attributes=raw_entity.get("attributes", {})
                    )
                    created = True
                
                processed_entities.append(entity)
                entity_map[name] = {
                    "id": entity.id,
                    "created": created,
                    "entity": entity
                }
                
            except Exception as e:
                logger.error(f"Failed to process entity: {raw_entity}. Error: {e}")
                continue
        
        # Save all entities
        if processed_entities:
            self.storage.save_entities(processed_entities)
        
        return entity_map
    
    def _process_relationships(self, raw_relationships: List[Dict[str, Any]], entity_map: Dict[str, Dict[str, Any]], meeting_id: str) -> List[EntityRelationship]:
        """Process relationships with validation."""
        relationships = []
        
        for raw_rel in raw_relationships:
            from_name = raw_rel.get("from", "").strip()
            to_name = raw_rel.get("to", "").strip()
            rel_type = self._validate_relationship_type(raw_rel.get("type", ""))
            
            if not from_name or not to_name or not rel_type:
                continue
            
            # Resolve entities
            from_entity = entity_map.get(from_name)
            to_entity = entity_map.get(to_name)
            
            if not from_entity or not to_entity:
                # Try to resolve using entity resolver
                if not from_entity:
                    resolved = self.entity_resolver.resolve_entities([from_name])
                    if from_name in resolved and resolved[from_name].entity:
                        from_entity = {
                            "id": resolved[from_name].entity.id,
                            "entity": resolved[from_name].entity
                        }
                
                if not to_entity:
                    resolved = self.entity_resolver.resolve_entities([to_name])
                    if to_name in resolved and resolved[to_name].entity:
                        to_entity = {
                            "id": resolved[to_name].entity.id,
                            "entity": resolved[to_name].entity
                        }
            
            if from_entity and to_entity:
                relationship = EntityRelationship(
                    from_entity_id=from_entity["id"],
                    to_entity_id=to_entity["id"],
                    relationship_type=rel_type,
                    attributes=raw_rel.get("attributes", {}),
                    meeting_id=meeting_id
                )
                relationships.append(relationship)
        
        # Save relationships
        if relationships:
            self.storage.save_relationships(relationships)
        
        return relationships
    
    def _update_memory_mentions(self, memories: List[Memory], entity_map: Dict[str, Dict[str, Any]]):
        """Update memory entity mentions with resolved IDs."""
        for memory in memories:
            resolved_mentions = []
            
            for mention in memory.entity_mentions:
                if mention in entity_map:
                    resolved_mentions.append(entity_map[mention]["id"])
                else:
                    # Try to resolve
                    resolved = self.entity_resolver.resolve_entities([mention])
                    if mention in resolved and resolved[mention].entity:
                        resolved_mentions.append(resolved[mention].entity.id)
            
            memory.entity_mentions = resolved_mentions
    
    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for matching."""
        return name.lower().strip()
    
    def _validate_entity_type(self, type_str: str) -> Optional[EntityType]:
        """Validate and convert entity type string."""
        try:
            return EntityType(type_str.lower())
        except ValueError:
            logger.warning(f"Invalid entity type: {type_str}")
            return None
    
    def _validate_relationship_type(self, type_str: str) -> Optional[RelationshipType]:
        """Validate and convert relationship type string."""
        try:
            return RelationshipType(type_str.lower())
        except ValueError:
            logger.warning(f"Invalid relationship type: {type_str}")
            return None