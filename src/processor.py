"""Process extracted entities and track state changes."""

from typing import List, Dict, Any, Optional
from datetime import datetime
import threading
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

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class EntityProcessor:
    """Process entities, states, and relationships from extraction results."""

    def __init__(self, storage: MemoryStorage):
        """Initialize with storage and embedding engine."""
        self.storage = storage
        self.embeddings = EmbeddingEngine()

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

        # 3. Process state changes
        transitions = self._process_state_changes(
            extraction.states, entity_map, meeting_id
        )
        results["state_transitions"] = len(transitions)

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

                # Save current state if provided
                if "current_state" in raw_entity and raw_entity["current_state"]:
                    state = EntityState(
                        entity_id=entity.id,
                        state=raw_entity["current_state"],
                        meeting_id=meeting_id,
                    )
                    self.storage.save_entity_states([state])
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

    def _find_best_match(
        self, name: str, entity_map: Dict[str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find the best entity match using direct lookup and fuzzy matching."""
        # Try direct lookup first
        direct_match = entity_map.get(name)
        if direct_match:
            return direct_match

        # Fallback to fuzzy matching
        choices = list(entity_map.keys())
        if not choices:
            return None

        best_match, score = process.extractOne(name, choices)
        if score > 80:  # Confidence threshold
            logging.info(f"Fuzzy matched '{name}' to '{best_match}' with score {score}")
            return entity_map[best_match]

        logging.warning(
            f"Could not find a suitable match for '{name}'. Best guess '{best_match}' with score {score} was below threshold."
        )
        return None

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

            # Resolve entity IDs with fuzzy matching
            from_entity = self._find_best_match(from_name, entity_map)
            to_entity = self._find_best_match(to_name, entity_map)

            if not from_entity or not to_entity:
                logging.warning(
                    f"Could not resolve entities for relationship: {from_name} -> {to_name}. Skipping."
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
        """Process state changes and create transitions."""
        transitions = []

        for raw_change in raw_changes:
            entity_name = raw_change.get("entity", "").strip()
            entity_info = entity_map.get(entity_name)

            if not entity_info:
                continue

            entity_id = entity_info["id"]

            # Get previous state
            previous_state = self.storage.get_entity_current_state(entity_id)

            # New state from extraction
            new_state = raw_change.get("to_state", {})

            # Detect actual changes
            if previous_state:
                changed_fields = self._detect_changes(previous_state, new_state)
                if not changed_fields:
                    continue  # No actual changes
            else:
                # First time seeing this entity state
                changed_fields = list(new_state.keys())

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

        # Save transitions
        if transitions:
            self.storage.save_transitions(transitions)

        return transitions

    def _update_memory_mentions(
        self, memories: List[Any], entity_map: Dict[str, Dict[str, Any]]
    ):
        """Update memory objects with resolved entity IDs."""
        for memory in memories:
            resolved_mentions = []

            for mention in memory.entity_mentions:
                if mention in entity_map:
                    resolved_mentions.append(entity_map[mention]["id"])
                else:
                    # Try fuzzy matching
                    for name, info in entity_map.items():
                        if (
                            mention.lower() in name.lower()
                            or name.lower() in mention.lower()
                        ):
                            resolved_mentions.append(info["id"])
                            break

            memory.entity_mentions = resolved_mentions

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

    def _detect_changes(
        self, old_state: Dict[str, Any], new_state: Dict[str, Any]
    ) -> List[str]:
        """Detect which fields changed between states."""
        changed = []

        # Check for changed values
        for key, new_value in new_state.items():
            old_value = old_state.get(key)

            if old_value != new_value:
                changed.append(key)

        # Check for removed fields
        for key in old_state:
            if key not in new_state:
                changed.append(key)

        return changed
    
    def _generate_embeddings_async(self, entities: List[Entity]):
        """Generate embeddings for entities in a background thread."""
        def generate():
            for entity in entities:
                try:
                    # Generate embedding
                    embedding = self.embeddings.encode(entity.name)
                    if embedding.ndim > 1:
                        embedding = embedding[0]
                    
                    # Update in database
                    self.storage.update_entity_embedding(entity.id, embedding)
                    logging.info(f"Generated embedding for entity: {entity.name}")
                    
                except Exception as e:
                    logging.error(f"Failed to generate embedding for {entity.name}: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=generate, daemon=True)
        thread.start()
        logging.info(f"Started background embedding generation for {len(entities)} entities")
