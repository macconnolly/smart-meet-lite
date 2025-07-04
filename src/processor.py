"""Process extracted entities and track state changes."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
from .entity_resolver import EntityResolver
from .models import (
    Entity,
    EntityState,
    EntityRelationship,
    StateTransition,
    EntityType,
    RelationshipType,
    ExtractionResult,
)
from .storage import MemoryStorage
from .embeddings import EmbeddingEngine
import logging
from fuzzywuzzy import process
from .config import settings

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class EntityProcessor:
    """Process entities, states, and relationships from extraction results."""

    def __init__(self, storage: MemoryStorage, entity_resolver: EntityResolver):
        """Initialize with storage and embedding engine."""
        self.storage = storage
        self.entity_resolver = entity_resolver
        self.embeddings = entity_resolver.embeddings

    def process_extraction(
        self, extraction: ExtractionResult, meeting_id: str
    ) -> Dict[str, Any]:
        """Process extraction results and update entity graph."""
        results = {
            "entities_created": 0,
            "entities_updated": 0,
            "relationships_created": 0,
            "state_transitions": 0,
            "entity_map": {},  # Map from extracted names to entity IDs
        }

        # 1. Process entities
        entity_map = self._process_entities(extraction.entities, meeting_id)
        results["entity_map"] = entity_map
        results["entities_created"] = len(
            [e for e in entity_map.values() if e["created"]]
        )
        results["entities_updated"] = len(
            [e for e in entity_map.values() if not e["created"]]
        )

        # 2. Process relationships
        relationships = self._process_relationships(
            extraction.relationships, entity_map, meeting_id
        )
        results["relationships_created"] = len(relationships)

        # 3. Process state changes from both explicit changes and current states
        explicit_transitions = self._process_state_changes(
            extraction.states, entity_map, meeting_id
        )
        
        # 3b. Process implicit state changes by comparing current states
        implicit_transitions = self._detect_implicit_state_changes(
            entity_map, meeting_id, extraction
        )
        
        all_transitions = explicit_transitions + implicit_transitions
        results["state_transitions"] = len(all_transitions)

        # 4. Update memory entity mentions with resolved IDs
        self._update_memory_mentions(extraction.memories, entity_map)

        # 5. Update meeting entity count
        unique_entity_ids = set(info["id"] for info in entity_map.values())
        self._update_meeting_entity_count(meeting_id, len(unique_entity_ids))

        return results

    def _process_entities(
        self, raw_entities: List[Dict[str, Any]], meeting_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Process and resolve entities."""
        entity_map = {}
        processed_entities = []

        for raw_entity in raw_entities:
            try:
                # Normalize entity name
                name = raw_entity.get("name", "").strip()
                normalized_name = self._normalize_name(name)
                entity_type = self._validate_entity_type(raw_entity.get("type", ""))

                if not name or not entity_type:
                    logging.warning(
                        f"Skipping entity with missing name or type: {raw_entity}"
                    )
                    continue

                # Try to find existing entity
                existing = self.storage.get_entity_by_name(normalized_name, entity_type)

                if existing:
                    # Update existing entity
                    entity = existing
                    created = False
                    logging.info(f"Found existing entity for '{name}'. ID: {entity.id}")

                    # Merge attributes
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
                        attributes=raw_entity.get("attributes", {}),
                    )
                    created = True
                    logging.info(f"Creating new entity: '{name}'")

                processed_entities.append(entity)
                entity_map[name] = {
                    "id": entity.id,
                    "created": created,
                    "entity": entity,
                }

                # Store current state for later processing (don't save yet!)
                if "current_state" in raw_entity and raw_entity["current_state"]:
                    entity_map[name]["current_state"] = raw_entity["current_state"]
                else:
                    # Try to infer state from context if not explicitly provided
                    inferred_state = self._infer_state_from_context(
                        name, 
                        entity_type.value,
                        extraction.meeting_metadata.get("transcript_context", "")
                    )
                    if inferred_state:
                        entity_map[name]["current_state"] = inferred_state
                        entity_map[name]["state_inferred"] = True
            except Exception as e:
                logging.error(f"Failed to process entity: {raw_entity}. Error: {e}")
                continue

        # Save all entities
        if processed_entities:
            self.storage.save_entities(processed_entities)
            
            # Generate embeddings for new entities in background
            new_entities = []
            for entity in processed_entities:
                # Check if entity was created (handle case variations)
                entity_info = entity_map.get(entity.name)
                if not entity_info:
                    # Try normalized name
                    for key, info in entity_map.items():
                        if self._normalize_name(key) == entity.normalized_name:
                            entity_info = info
                            break
                
                if entity_info and entity_info.get("created", False):
                    new_entities.append(entity)
                    
            if new_entities:
                self._generate_embeddings_async(new_entities)

        return entity_map

    def _resolve_entity_names(self, 
                             names: List[str], 
                             entity_map: Dict[str, Dict[str, Any]],
                             context: Optional[str] = None) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Resolve entity names using the shared EntityResolver.
        
        Args:
            names: List of entity names to resolve
            entity_map: Existing entities from current processing
            context: Optional context for better resolution
            
        Returns:
            Dict mapping names to entity info dicts (or None if not found)
        """
        if not names:
            return {}
        
        # First check entity_map for exact matches (entities just created)
        results = {}
        names_to_resolve = []
        
        for name in names:
            if name in entity_map:
                results[name] = entity_map[name]
            else:
                names_to_resolve.append(name)
        
        if not names_to_resolve:
            return results
        
        # Use EntityResolver for remaining names
        resolution_results = self.entity_resolver.resolve_entities(
            names_to_resolve,
            context=context
        )
        
        # Convert EntityMatch objects to entity_map format
        for name, match in resolution_results.items():
            if match.entity and match.confidence >= settings.entity_resolution_threshold:
                # Entity exists in database
                results[name] = {
                    "id": match.entity.id,
                    "created": False,
                    "entity": match.entity
                }
                logging.info(
                    f"Resolved '{name}' to existing entity '{match.entity.name}' "
                    f"with {match.confidence:.2f} confidence ({match.match_type})"
                )
            else:
                # No match or low confidence
                results[name] = None
                logging.warning(
                    f"Could not resolve '{name}' - "
                    f"best match had {match.confidence:.2f} confidence"
                )
        
        return results


    def _process_relationships(
        self,
        raw_relationships: List[Dict[str, Any]],
        entity_map: Dict[str, Dict[str, Any]],
        meeting_id: str,
    ) -> List[EntityRelationship]:
        """Process and create relationships with fuzzy matching fallback."""
        relationships = []

        for raw_rel in raw_relationships:
            from_name = raw_rel.get("from", "").strip()
            to_name = raw_rel.get("to", "").strip()
            rel_type = self._validate_relationship_type(raw_rel.get("type", ""))

            if not from_name or not to_name or not rel_type:
                logging.warning(f"Skipping incomplete relationship: {raw_rel}")
                continue

            # Resolve entity names using EntityResolver
            resolution_results = self._resolve_entity_names(
                [from_name, to_name],
                entity_map,
                context=f"Relationship: {from_name} {rel_type} {to_name}"
            )

            from_entity = resolution_results.get(from_name)
            to_entity = resolution_results.get(to_name)

            # Handle unresolved entities
            if not from_entity:
                logging.warning(f"Could not resolve from_entity: '{from_name}'")
                
            if not to_entity:
                # Check if this is an action item assignment to a deliverable
                if (rel_type in ["assigned_to", "responsible_for"] and 
                    settings.create_deliverables_on_assignment):
                    
                    # Auto-create deliverable entity
                    deliverable = Entity(
                        type=EntityType.TASK,
                        name=to_name,
                        normalized_name=self._normalize_name(to_name),
                        attributes={"auto_created": True, "from_action_item": True}
                    )
                    
                    # Save and generate embedding
                    self.storage.save_entities([deliverable])
                    embedding = self.embeddings.encode(deliverable.name)
                    self.storage.save_entity_embedding(deliverable.id, embedding)
                    
                    to_entity = {
                        "id": deliverable.id,
                        "created": True,
                        "entity": deliverable
                    }
                    
                    # Add to entity_map for future reference
                    entity_map[to_name] = to_entity
                    
                    logging.info(f"Auto-created deliverable entity: '{to_name}'")
                else:
                    logging.warning(f"Could not resolve to_entity: '{to_name}'")

            if not from_entity or not to_entity:
                logging.warning(
                    f"Skipping relationship due to unresolved entities: "
                    f"{from_name} -> {to_name}"
                )
                continue

            # Check if relationship already exists
            existing_rels = self.storage.get_entity_relationships(from_entity["id"])
            exists = any(
                r["to_entity"]["id"] == to_entity["id"]
                and r["relationship_type"] == rel_type
                and r["active"]
                for r in existing_rels
            )

            if not exists:
                relationship = EntityRelationship(
                    from_entity_id=from_entity["id"],
                    to_entity_id=to_entity["id"],
                    relationship_type=rel_type,
                    attributes=raw_rel.get("attributes", {}),
                    meeting_id=meeting_id,
                )
                relationships.append(relationship)
                logging.info(
                    f"Created new relationship: {from_entity['entity'].name} -> {to_entity['entity'].name} ({rel_type})"
                )

        # Save relationships
        if relationships:
            self.storage.save_relationships(relationships)

        return relationships

    def _process_state_changes(
        self,
        raw_changes: List[Dict[str, Any]],
        entity_map: Dict[str, Dict[str, Any]],
        meeting_id: str,
    ) -> List[StateTransition]:
        """Process explicit state changes from LLM extraction."""
        transitions = []
        processed_entities = set()  # Track which entities we've processed

        for raw_change in raw_changes:
            entity_name = raw_change.get("entity", "").strip()
            entity_info = entity_map.get(entity_name)

            # Try to resolve if not in entity_map
            if not entity_info:
                resolution_results = self._resolve_entity_names(
                    [entity_name],
                    entity_map,
                    context="State change tracking"
                )
                entity_info = resolution_results.get(entity_name)
                
                if not entity_info:
                    logging.warning(
                        f"Could not resolve entity for state change: '{entity_name}'"
                    )
                    continue

            entity_id = entity_info["id"]
            processed_entities.add(entity_id)

            # Get previous state
            previous_state = self.storage.get_entity_current_state(entity_id)
            logging.debug(f"[_process_state_changes] Entity: {entity_name}, ID: {entity_id}")
            logging.debug(f"[_process_state_changes] Previous state: {previous_state}")

            # New state from explicit change
            new_state = raw_change.get("to_state", {})
            logging.debug(f"[_process_state_changes] New state: {new_state}")

            # Detect actual changes
            if previous_state:
                changed_fields = self._detect_changes(previous_state, new_state)
                if not changed_fields:
                    logging.debug(f"[_process_state_changes] No actual changes detected for {entity_name}.")
                    continue  # No actual changes
                else:
                    logging.info(f"[_process_state_changes] Detected changes for {entity_name}: {changed_fields}")
            else:
                # First time seeing this entity state
                changed_fields = list(new_state.keys())
                logging.info(f"[_process_state_changes] First state for {entity_name}. All fields considered changed: {changed_fields}")

            # Create transition
            transition = StateTransition(
                entity_id=entity_id,
                from_state=previous_state,
                to_state=new_state,
                changed_fields=changed_fields,
                reason=raw_change.get("reason"),
                meeting_id=meeting_id,
            )
            transitions.append(transition)

            # Save new state
            state = EntityState(
                entity_id=entity_id, state=new_state, meeting_id=meeting_id
            )
            self.storage.save_entity_states([state])
            
            # Mark this entity as having explicit state change
            entity_info["explicit_state_processed"] = True

        # Save transitions
        if transitions:
            self.storage.save_transitions(transitions)

        return transitions

    def _update_memory_mentions(
        self, memories: List[Any], entity_map: Dict[str, Dict[str, Any]]
    ):
        """Update memory objects with resolved entity IDs using EntityResolver."""
        if not memories:
            return
        
        # Collect all unique mentions across all memories
        all_mentions = set()
        for memory in memories:
            all_mentions.update(memory.entity_mentions)
        
        # Batch resolve all mentions at once
        resolution_results = self._resolve_entity_names(
            list(all_mentions),
            entity_map,
            context="Memory entity mentions"
        )
        
        # Update each memory with resolved IDs
        for memory in memories:
            resolved_mentions = []
            
            for mention in memory.entity_mentions:
                entity_info = resolution_results.get(mention)
                if entity_info:
                    resolved_mentions.append(entity_info["id"])
                else:
                    logging.debug(f"Could not resolve mention: '{mention}'")
            
            memory.entity_mentions = resolved_mentions
            
        logging.info(
            f"Resolved {len([r for r in resolution_results.values() if r])}/"
            f"{len(all_mentions)} entity mentions across {len(memories)} memories"
        )

    def _update_meeting_entity_count(self, meeting_id: str, count: int):
        """Update the entity count for a meeting."""
        # This would be implemented in storage if needed
        pass

    def _normalize_name(self, name: str) -> str:
        """Normalize entity name for matching by lowercasing and stripping whitespace."""
        return name.lower().strip()

    def _validate_entity_type(self, type_str: str) -> Optional[EntityType]:
        """Validate and convert entity type string."""
        try:
            return EntityType(type_str.lower())
        except ValueError as e:
            logging.warning(f"Invalid entity type string: '{type_str}'. Error: {e}")
            return None

    def _validate_relationship_type(self, type_str: str) -> Optional[RelationshipType]:
        """Validate and convert relationship type string."""
        try:
            return RelationshipType(type_str.lower())
        except ValueError as e:
            logging.warning(
                f"Invalid relationship type string: '{type_str}'. Error: {e}"
            )
            return RelationshipType.RELATES_TO

    def _is_empty_state(self, state: Dict[str, Any]) -> bool:
        """Check if a state is empty (all None values or empty lists)."""
        if not state:
            return True
        
        for value in state.values():
            if value is not None and value != [] and value != "":
                return False
        
        return True
    
    def _detect_changes(
        self, old_state: Dict[str, Any], new_state: Dict[str, Any]
    ) -> List[str]:
        """Detect which fields changed between states."""
        changed = []
        logging.debug(f"[_detect_changes] Comparing old state: {old_state} with new state: {new_state}")

        # Check for changed values
        for key, new_value in new_state.items():
            old_value = old_state.get(key)
            logging.debug(f"[_detect_changes] Key: {key}, Old: {old_value}, New: {new_value}")
            if old_value != new_value:
                changed.append(key)
                logging.debug(f"[_detect_changes] Change detected for key: {key}")

        # Check for removed fields
        for key in old_state:
            if key not in new_state:
                changed.append(key)
                logging.debug(f"[_detect_changes] Field removed: {key}")

        logging.debug(f"[_detect_changes] All changed fields: {changed}")
        return changed
    
    def _detect_implicit_state_changes(
        self, entity_map: Dict[str, Dict[str, Any]], meeting_id: str, extraction: Any
    ) -> List[StateTransition]:
        """Detect state changes by comparing current states with previous states."""
        transitions = []
        
        for entity_name, entity_info in entity_map.items():
            # Skip if no current state extracted
            if "current_state" not in entity_info:
                continue
            
            # Skip if already processed as explicit state change
            if entity_info.get("explicit_state_processed", False):
                logging.debug(f"Skipping '{entity_name}' - already processed as explicit state change")
                continue
                
            entity_id = entity_info["id"]
            current_state = entity_info["current_state"]
            
            # Check if state is all None values - if so, skip to preserve previous state
            if self._is_empty_state(current_state):
                logging.debug(f"Skipping empty state for '{entity_name}' - preserving previous state")
                continue
            
            # Get previous state
            previous_state = self.storage.get_entity_current_state(entity_id)
            
            # If no previous state, this is the first state
            if not previous_state:
                logging.info(f"First state for entity '{entity_name}': {current_state}")
                # Save as new state
                state = EntityState(
                    entity_id=entity_id,
                    state=current_state,
                    meeting_id=meeting_id
                )
                self.storage.save_entity_states([state])
                
                # Create transition for first state
                transition = StateTransition(
                    entity_id=entity_id,
                    from_state=None,
                    to_state=current_state,
                    changed_fields=list(current_state.keys()),
                    reason="Initial state from meeting",
                    meeting_id=meeting_id
                )
                transitions.append(transition)
                continue
            
            # Detect changes
            changed_fields = self._detect_changes(previous_state, current_state)
            
            if changed_fields:
                logging.info(f"State changes detected for '{entity_name}': {changed_fields}")
                
                # Save new state
                state = EntityState(
                    entity_id=entity_id,
                    state=current_state,
                    meeting_id=meeting_id
                )
                self.storage.save_entity_states([state])
                
                # Create transition
                transition = StateTransition(
                    entity_id=entity_id,
                    from_state=previous_state,
                    to_state=current_state,
                    changed_fields=changed_fields,
                    reason=self._infer_change_reason(entity_name, changed_fields, extraction),
                    meeting_id=meeting_id
                )
                transitions.append(transition)
            else:
                logging.debug(f"No state changes for '{entity_name}'")
        
        if transitions:
            self.storage.save_transitions(transitions)
            
        return transitions
    
    def _infer_state_from_context(
        self, entity_name: str, entity_type: str, transcript_context: str
    ) -> Optional[Dict[str, Any]]:
        """Infer entity state from context using patterns."""
        entity_lower = entity_name.lower()
        context_lower = transcript_context.lower()
        
        # Pattern-based state inference
        state_patterns = {
            # Progress patterns
            "in_progress": [
                f"{entity_lower} is in progress",
                f"working on {entity_lower}",
                f"{entity_lower} is underway", 
                f"started {entity_lower}",
                f"{entity_lower} has started",
                f"currently working on {entity_lower}",
                f"{entity_lower} is being worked on",
                f"progress on {entity_lower}"
            ],
            "completed": [
                f"{entity_lower} is complete",
                f"{entity_lower} is done",
                f"finished {entity_lower}",
                f"completed {entity_lower}",
                f"{entity_lower} has been completed",
                f"{entity_lower} is now complete"
            ],
            "blocked": [
                f"{entity_lower} is blocked",
                f"{entity_lower} is waiting",
                f"blocked on {entity_lower}",
                f"waiting for .* {entity_lower}",
                f"{entity_lower} needs",
                f"can't proceed with {entity_lower}"
            ],
            "planned": [
                f"{entity_lower} is planned",
                f"planning {entity_lower}",
                f"will start {entity_lower}",
                f"{entity_lower} scheduled for",
                f"upcoming {entity_lower}"
            ]
        }
        
        # Check patterns
        inferred_state = {}
        for status, patterns in state_patterns.items():
            for pattern in patterns:
                if pattern in context_lower:
                    inferred_state["status"] = status
                    logging.info(f"Inferred status '{status}' for '{entity_name}' from pattern: {pattern}")
                    break
            if "status" in inferred_state:
                break
        
        # Extract assigned person if mentioned
        assignment_patterns = [
            rf"(\w+\s+\w+) (?:is|will be) (?:leading|working on|responsible for|owns) {entity_lower}",
            rf"{entity_lower} (?:is|will be) (?:led by|assigned to|owned by) (\w+\s+\w+)",
            rf"(\w+\s+\w+) (?:reports|reported) .* {entity_lower}"
        ]
        
        import re
        for pattern in assignment_patterns:
            match = re.search(pattern, transcript_context, re.IGNORECASE)
            if match:
                assigned_to = match.group(1)
                inferred_state["assigned_to"] = assigned_to
                logging.info(f"Inferred assignment '{assigned_to}' for '{entity_name}'")
                break
        
        return inferred_state if inferred_state else None
    
    def _infer_change_reason(
        self, entity_name: str, changed_fields: List[str], extraction: Any
    ) -> str:
        """Infer the reason for state changes from the meeting content."""
        # Look for mentions of the entity in memories
        reasons = []
        
        for memory in extraction.memories:
            if entity_name.lower() in memory.content.lower():
                # Check for change-related keywords
                change_keywords = [
                    "now", "updated", "changed", "moved to", "transitioned",
                    "completed", "started", "blocked", "unblocked", "assigned"
                ]
                
                for keyword in change_keywords:
                    if keyword in memory.content.lower():
                        reasons.append(memory.content[:200])  # First 200 chars
                        break
        
        if reasons:
            return f"Based on discussion: {reasons[0]}"
        else:
            return f"State updated for fields: {', '.join(changed_fields)}"
    
    def _generate_embeddings_async(self, entities: List[Entity]):
        """Generate embeddings for entities in a background thread."""
        def generate():
            for entity in entities:
                try:
                    # Generate embedding
                    embedding = self.embeddings.encode(entity.name)
                    if embedding.ndim > 1:
                        embedding = embedding[0]
                    
                    # Save to Qdrant
                    self.storage.save_entity_embedding(entity.id, embedding)
                    logging.info(f"Generated embedding for entity: {entity.name}")
                    
                except Exception as e:
                    logging.error(f"Failed to generate embedding for {entity.name}: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
        logging.info(f"Started background embedding generation for {len(entities)} entities")
