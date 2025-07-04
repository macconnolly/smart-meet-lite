"""Enhanced storage layer with entity tracking and business intelligence."""

import sqlite3
import json
from typing import List, Optional, Dict, Any, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
import numpy as np
from datetime import datetime
from .models import (
    Memory,
    Meeting,
    SearchResult,
    Entity,
    EntityState,
    EntityRelationship,
    StateTransition,
    EntityType,
)
from .config import settings


class MemoryStorage:
    """Enhanced storage with entity tracking and BI capabilities."""

    def __init__(self):
        """Initialize storage connections."""
        self.db_path = settings.database_path
        self.collection_name = settings.qdrant_collection

        # Initialize SQLite with enhanced schema
        self._init_sqlite()

        # Initialize Qdrant
        self.qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        self._init_qdrant()

    def _init_sqlite(self):
        """Create enhanced SQLite tables for business intelligence."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Original tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS meetings (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                transcript TEXT NOT NULL,
                participants TEXT,
                date TIMESTAMP,
                summary TEXT,
                topics TEXT,
                key_decisions TEXT,
                action_items TEXT,
                created_at TIMESTAMP NOT NULL,
                memory_count INTEGER DEFAULT 0,
                entity_count INTEGER DEFAULT 0,
                email_metadata TEXT,
                project_tags TEXT,
                meeting_type TEXT,
                actual_start_time TIMESTAMP,
                actual_end_time TIMESTAMP,
                detailed_summary TEXT,
                raw_extraction TEXT,
                organization_context TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                content TEXT NOT NULL,
                speaker TEXT,
                timestamp TEXT,
                metadata TEXT,
                entity_mentions TEXT,
                embedding_id TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )

        # Entity tracking tables
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                normalized_name TEXT NOT NULL,
                attributes TEXT,
                first_seen TIMESTAMP NOT NULL,
                last_updated TIMESTAMP NOT NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_states (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                state TEXT NOT NULL,
                meeting_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                confidence REAL DEFAULT 1.0,
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS entity_relationships (
                id TEXT PRIMARY KEY,
                from_entity_id TEXT NOT NULL,
                to_entity_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                attributes TEXT,
                meeting_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (from_entity_id) REFERENCES entities(id),
                FOREIGN KEY (to_entity_id) REFERENCES entities(id),
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS state_transitions (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT NOT NULL,
                changed_fields TEXT,
                reason TEXT,
                meeting_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (entity_id) REFERENCES entities(id),
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )

        # Indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_normalized ON entities(normalized_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_states_entity ON entity_states(entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_from ON entity_relationships(from_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_relationships_to ON entity_relationships(to_entity_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_transitions_entity ON state_transitions(entity_id)"
        )
        
        # New indexes for performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_normalized_name ON entities(normalized_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_entities_last_updated ON entities(last_updated)"
        )
        
        # New tables for enhanced meeting intelligence
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS meeting_deliverables (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                target_audience TEXT,
                requirements TEXT,
                discussed_evolution TEXT,
                dependencies TEXT,
                deadline TEXT,
                format_preferences TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stakeholder_intelligence (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                stakeholder TEXT NOT NULL,
                role TEXT,
                communication_preferences TEXT,
                noted_concerns TEXT,
                format_preferences TEXT,
                questions_asked TEXT,
                key_interests TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions_with_context (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT,
                stakeholders_involved TEXT,
                impact_areas TEXT,
                supersedes_decision TEXT,
                decision_status TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS risk_areas (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                risk TEXT NOT NULL,
                severity TEXT NOT NULL,
                mitigation_approach TEXT,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )
        
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cross_project_impacts (
                id TEXT PRIMARY KEY,
                meeting_id TEXT NOT NULL,
                project TEXT NOT NULL,
                impact_description TEXT NOT NULL,
                coordination_needed BOOLEAN DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY (meeting_id) REFERENCES meetings(id)
            )
        """
        )
        
        # Indexes for new tables
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deliverables_meeting ON meeting_deliverables(meeting_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stakeholder_meeting ON stakeholder_intelligence(meeting_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_decisions_meeting ON decisions_with_context(meeting_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_risks_meeting ON risk_areas(meeting_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_impacts_meeting ON cross_project_impacts(meeting_id)")
        
        # CRITICAL: Add missing index for memories table to prevent timeouts
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_meeting_id ON memories(meeting_id)")

        conn.commit()
        conn.close()

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert a database row to an Entity object.
        
        Handles sqlite3.Row objects properly.
        """
        return Entity(
            id=row['id'],
            type=EntityType(row['type']),
            name=row['name'],
            normalized_name=row['normalized_name'],
            attributes=json.loads(row['attributes']) if row['attributes'] else {},
            first_seen=datetime.fromisoformat(row['first_seen']),
            last_updated=datetime.fromisoformat(row['last_updated'])
        )

    def _init_qdrant(self):
        """Create Qdrant collection."""
        collections = self.qdrant.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        
        # Ensure entity embeddings collection exists
        entity_exists = any(c.name == settings.qdrant_entity_collection for c in collections)
        if not entity_exists:
            self.qdrant.create_collection(
                collection_name=settings.qdrant_entity_collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),  # Assuming 384-dim embeddings
            )

    def save_meeting(self, meeting: Meeting) -> str:
        """Save meeting to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO meetings 
            (id, title, transcript, participants, date, summary, topics, 
             key_decisions, action_items, created_at, memory_count, entity_count,
             email_metadata, project_tags, meeting_type, actual_start_time, 
             actual_end_time, detailed_summary, raw_extraction, organization_context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                meeting.id,
                meeting.title,
                meeting.transcript,
                json.dumps(meeting.participants),
                meeting.date.isoformat() if meeting.date else None,
                meeting.summary,
                json.dumps(meeting.topics),
                json.dumps(meeting.key_decisions),
                json.dumps(meeting.action_items),
                meeting.created_at.isoformat(),
                meeting.memory_count,
                meeting.entity_count,
                json.dumps(meeting.email_metadata) if hasattr(meeting, 'email_metadata') and meeting.email_metadata else None,
                json.dumps(meeting.project_tags) if hasattr(meeting, 'project_tags') and meeting.project_tags else None,
                meeting.meeting_type if hasattr(meeting, 'meeting_type') else None,
                meeting.actual_start_time.isoformat() if hasattr(meeting, 'actual_start_time') and meeting.actual_start_time else None,
                meeting.actual_end_time.isoformat() if hasattr(meeting, 'actual_end_time') and meeting.actual_end_time else None,
                meeting.detailed_summary if hasattr(meeting, 'detailed_summary') else None,
                json.dumps(meeting.raw_extraction) if hasattr(meeting, 'raw_extraction') and meeting.raw_extraction else None,
                meeting.organization_context if hasattr(meeting, 'organization_context') else None,
            ),
        )

        conn.commit()
        conn.close()

        return meeting.id

    def save_entities(self, entities: List[Entity]) -> List[str]:
        """Save or update entities."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved_ids = []
        for entity in entities:
            # Check if entity already exists
            cursor.execute(
                """
                SELECT id, attributes FROM entities 
                WHERE normalized_name = ? AND type = ?
            """,
                (entity.normalized_name, entity.type),
            )

            existing = cursor.fetchone()

            if existing:
                # Update existing entity
                entity_id = existing[0]
                old_attrs = json.loads(existing[1]) if existing[1] else {}
                # Merge attributes
                merged_attrs = {**old_attrs, **entity.attributes}

                cursor.execute(
                    """
                    UPDATE entities 
                    SET attributes = ?, last_updated = ?
                    WHERE id = ?
                """,
                    (json.dumps(merged_attrs), datetime.now().isoformat(), entity_id),
                )

                saved_ids.append(entity_id)
            else:
                # Insert new entity
                cursor.execute(
                    """
                    INSERT INTO entities 
                    (id, type, name, normalized_name, attributes, first_seen, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        entity.id,
                        entity.type,
                        entity.name,
                        entity.normalized_name,
                        json.dumps(entity.attributes),
                        entity.first_seen.isoformat(),
                        entity.last_updated.isoformat(),
                    ),
                )
                saved_ids.append(entity.id)

        conn.commit()
        conn.close()

        return saved_ids

    def save_entity_states(self, states: List[EntityState]) -> None:
        """Save entity states."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for state in states:
            cursor.execute(
                """
                INSERT INTO entity_states 
                (id, entity_id, state, meeting_id, timestamp, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    state.id,
                    state.entity_id,
                    json.dumps(state.state),
                    state.meeting_id,
                    state.timestamp.isoformat(),
                    state.confidence,
                ),
            )

        conn.commit()
        conn.close()

    def save_relationships(self, relationships: List[EntityRelationship]) -> None:
        """Save entity relationships."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for rel in relationships:
            cursor.execute(
                """
                INSERT INTO entity_relationships 
                (id, from_entity_id, to_entity_id, relationship_type, 
                 attributes, meeting_id, timestamp, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    rel.id,
                    rel.from_entity_id,
                    rel.to_entity_id,
                    rel.relationship_type,
                    json.dumps(rel.attributes),
                    rel.meeting_id,
                    rel.timestamp.isoformat(),
                    rel.active,
                ),
            )

        conn.commit()
        conn.close()

    def save_transitions(self, transitions: List[StateTransition]) -> None:
        """Save state transitions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for trans in transitions:
            cursor.execute(
                """
                INSERT INTO state_transitions 
                (id, entity_id, from_state, to_state, changed_fields, 
                 reason, meeting_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    trans.id,
                    trans.entity_id,
                    json.dumps(trans.from_state) if trans.from_state else None,
                    json.dumps(trans.to_state),
                    json.dumps(trans.changed_fields),
                    trans.reason,
                    trans.meeting_id,
                    trans.timestamp.isoformat(),
                ),
            )

        conn.commit()
        conn.close()

    def update_meeting_raw_extraction(self, meeting_id: str, extraction_data: Dict[str, Any]) -> None:
        """Store raw extraction data and detailed summary for future reference."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            UPDATE meetings 
            SET raw_extraction = ?,
                detailed_summary = ?
            WHERE id = ?
            """,
            (
                json.dumps(extraction_data) if extraction_data else None,
                extraction_data.get('detailed_summary', '') if extraction_data else '',
                meeting_id
            )
        )
        
        conn.commit()
        conn.close()
    
    def save_meeting_deliverables(self, meeting_id: str, deliverables: List[Dict[str, Any]]) -> None:
        """Save deliverable intelligence from meeting."""
        if not deliverables:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for deliverable in deliverables:
            import uuid
            cursor.execute(
                """
                INSERT INTO meeting_deliverables 
                (id, meeting_id, name, type, target_audience, requirements, 
                 discussed_evolution, dependencies, deadline, format_preferences, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    meeting_id,
                    deliverable.get("name"),
                    deliverable.get("type"),
                    json.dumps(deliverable.get("target_audience", [])),
                    json.dumps(deliverable.get("requirements", [])),
                    deliverable.get("discussed_evolution"),
                    json.dumps(deliverable.get("dependencies", [])),
                    deliverable.get("deadline"),
                    deliverable.get("format_preferences"),
                    datetime.now().isoformat()
                )
            )
        
        conn.commit()
        conn.close()
    
    def save_stakeholder_intelligence(self, meeting_id: str, stakeholders: List[Dict[str, Any]]) -> None:
        """Save stakeholder intelligence from meeting."""
        if not stakeholders:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for stakeholder in stakeholders:
            import uuid
            cursor.execute(
                """
                INSERT INTO stakeholder_intelligence
                (id, meeting_id, stakeholder, role, communication_preferences,
                 noted_concerns, format_preferences, questions_asked, key_interests, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    meeting_id,
                    stakeholder.get("stakeholder"),
                    stakeholder.get("role"),
                    stakeholder.get("communication_preferences"),
                    json.dumps(stakeholder.get("noted_concerns", [])),
                    stakeholder.get("format_preferences"),
                    json.dumps(stakeholder.get("questions_asked", [])),
                    json.dumps(stakeholder.get("key_interests", [])),
                    datetime.now().isoformat()
                )
            )
        
        conn.commit()
        conn.close()
    
    def save_decisions_with_context(self, meeting_id: str, decisions: List[Dict[str, Any]]) -> None:
        """Save decisions with full context."""
        if not decisions:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for decision in decisions:
            import uuid
            cursor.execute(
                """
                INSERT INTO decisions_with_context
                (id, meeting_id, decision, rationale, stakeholders_involved,
                 impact_areas, supersedes_decision, decision_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    meeting_id,
                    decision.get("decision"),
                    decision.get("rationale"),
                    json.dumps(decision.get("stakeholders_involved", [])),
                    json.dumps(decision.get("impact_areas", [])),
                    decision.get("supersedes_decision"),
                    decision.get("decision_status", "proposed"),
                    datetime.now().isoformat()
                )
            )
        
        conn.commit()
        conn.close()
    
    def save_risk_areas(self, meeting_id: str, risks: List[Dict[str, Any]]) -> None:
        """Save identified risks from meeting."""
        if not risks:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for risk in risks:
            import uuid
            cursor.execute(
                """
                INSERT INTO risk_areas
                (id, meeting_id, risk, severity, mitigation_approach, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    meeting_id,
                    risk.get("risk"),
                    risk.get("severity", "medium"),
                    risk.get("mitigation_approach"),
                    datetime.now().isoformat()
                )
            )
        
        conn.commit()
        conn.close()

    def get_entity_by_name(
        self, name: str, entity_type: Optional[str] = None
    ) -> Optional[Entity]:
        """Get entity by normalized name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        normalized = name.lower().strip()

        if entity_type:
            cursor.execute(
                """
                SELECT * FROM entities 
                WHERE normalized_name = ? AND type = ?
            """,
                (normalized, entity_type),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM entities 
                WHERE normalized_name = ?
            """,
                (normalized,),
            )

        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_entity(row)
        return None

    def get_entity_current_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the current state of an entity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT state FROM entity_states 
            WHERE entity_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """,
            (entity_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])

        return None

    def get_entity_relationships(
        self, entity_id: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all relationships for an entity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
            SELECT r.*, 
                   e1.name as from_name, e1.type as from_type,
                   e2.name as to_name, e2.type as to_type
            FROM entity_relationships r
            JOIN entities e1 ON r.from_entity_id = e1.id
            JOIN entities e2 ON r.to_entity_id = e2.id
            WHERE (r.from_entity_id = ? OR r.to_entity_id = ?)
        """

        if active_only:
            query += " AND r.active = 1"

        cursor.execute(query, (entity_id, entity_id))

        relationships = []
        for row in cursor.fetchall():
            relationships.append(
                {
                    "id": row[0],
                    "from_entity": {"id": row[1], "name": row[8], "type": row[9]},
                    "to_entity": {"id": row[2], "name": row[10], "type": row[11]},
                    "relationship_type": row[3],
                    "attributes": json.loads(row[4]) if row[4] else {},
                    "meeting_id": row[5],
                    "timestamp": row[6],
                    "active": bool(row[7]),
                }
            )

        conn.close()
        return relationships

    def get_entity_timeline(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get timeline of state changes for an entity."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT t.*, m.title as meeting_title, m.date as meeting_date
            FROM state_transitions t
            JOIN meetings m ON t.meeting_id = m.id
            WHERE t.entity_id = ?
            ORDER BY t.timestamp DESC
        """,
            (entity_id,),
        )

        timeline = []
        for row in cursor.fetchall():
            timeline.append(
                {
                    "id": row[0],
                    "from_state": json.loads(row[2]) if row[2] else None,
                    "to_state": json.loads(row[3]),
                    "changed_fields": json.loads(row[4]) if row[4] else [],
                    "reason": row[5],
                    "meeting_id": row[6],
                    "meeting_title": row[8],
                    "meeting_date": row[9],
                    "timestamp": row[7],
                }
            )

        conn.close()
        return timeline

    def search_entities(
        self, query: str, entity_type: Optional[str] = None
    ) -> List[Entity]:
        """Search for entities by name or attributes."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Simple fuzzy search
        search_pattern = f"%{query}%"

        if entity_type:
            cursor.execute(
                """
                SELECT * FROM entities 
                WHERE (name LIKE ? OR attributes LIKE ?) AND type = ?
                ORDER BY last_updated DESC
            """,
                (search_pattern, search_pattern, entity_type),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM entities 
                WHERE name LIKE ? OR attributes LIKE ?
                ORDER BY last_updated DESC
            """,
                (search_pattern, search_pattern),
            )

        entities = []
        for row in cursor.fetchall():
            entities.append(self._row_to_entity(row))

        conn.close()
        return entities

    def get_all_entities(self, 
                        entity_type: Optional[EntityType] = None,
                        limit: Optional[int] = None,
                        offset: int = 0) -> List[Entity]:
        """
        Get all entities with optional filtering and pagination.
        
        Args:
            entity_type: Filter by entity type
            limit: Maximum number of entities to return
            offset: Number of entities to skip
            
        Returns:
            List of Entity objects
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM entities"
        params = []
        
        if entity_type:
            query += " WHERE type = ?"
            params.append(entity_type.value)
        
        query += " ORDER BY last_updated DESC"
        
        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        entities = []
        for row in cursor.fetchall():
            entities.append(self._row_to_entity(row))
        
        conn.close()
        return entities

    def save_entity_embedding(self, entity_id: str, embedding: np.ndarray):
        """Save a single entity's name embedding to Qdrant."""
        if embedding.ndim > 1:
            embedding = embedding.squeeze()  # Ensure 1D vector
        
        self.qdrant.upsert(
            collection_name=settings.qdrant_entity_collection,
            points=[
                PointStruct(
                    id=entity_id,
                    vector=embedding.tolist(),
                    payload={"entity_id": entity_id}  # Store ID in payload for consistency
                )
            ]
        )

    def get_entity_embedding(self, entity_id: str) -> Optional[np.ndarray]:
        """Retrieve a single entity's name embedding from Qdrant."""
        try:
            points = self.qdrant.retrieve(
                collection_name=settings.qdrant_entity_collection,
                ids=[entity_id],
                with_vectors=True
            )
            if points:
                return np.array(points[0].vector, dtype=np.float32)
        except Exception as e:
            # Log error, e.g., entity not found in Qdrant
            import logging
            logging.warning(f"Could not retrieve embedding for entity {entity_id} from Qdrant: {e}")
        return None

    def search_entity_embeddings(self, query_embedding: np.ndarray, limit: int = 5) -> List[Tuple[str, float]]:
        """Search for similar entity embeddings in Qdrant."""
        if query_embedding.ndim > 1:
            query_embedding = query_embedding.squeeze()  # Ensure 1D vector
        
        results = self.qdrant.search(
            collection_name=settings.qdrant_entity_collection,
            query_vector=query_embedding.tolist(),
            limit=limit,
            with_payload=False  # Only need ID and score
        )
        return [(result.id, result.score) for result in results]

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT * FROM entities
            WHERE id = ?
            """,
            (entity_id,),
        )
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_entity(row)
        return None

    def get_analytics_data(
        self, metric: str, time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Get analytics data for various metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        analytics = {}

        if metric == "entity_counts":
            cursor.execute(
                """
                SELECT type, COUNT(*) as count 
                FROM entities 
                GROUP BY type
            """
            )
            analytics["by_type"] = dict(cursor.fetchall())

        elif metric == "relationship_network":
            cursor.execute(
                """
                SELECT relationship_type, COUNT(*) as count 
                FROM entity_relationships 
                WHERE active = 1
                GROUP BY relationship_type
            """
            )
            analytics["by_relationship"] = dict(cursor.fetchall())

        elif metric == "state_changes":
            query = """
                SELECT DATE(timestamp) as date, COUNT(*) as changes
                FROM state_transitions
            """
            if time_range:
                query += " WHERE timestamp BETWEEN ? AND ?"
                cursor.execute(
                    query + " GROUP BY DATE(timestamp)",
                    (time_range[0].isoformat(), time_range[1].isoformat()),
                )
            else:
                cursor.execute(query + " GROUP BY DATE(timestamp)")

            analytics["by_date"] = dict(cursor.fetchall())

        conn.close()
        return analytics

    # Original methods remain the same
    def save_memories(
        self, memories: List[Memory], embeddings: np.ndarray
    ) -> List[str]:
        """Save memories and their embeddings."""
        if len(memories) != len(embeddings):
            raise ValueError("Number of memories must match number of embeddings")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Prepare points for Qdrant
        points = []
        for i, memory in enumerate(memories):
            # Get embedding and ensure it's 1D
            embedding = embeddings[i]
            if embedding.ndim > 1:
                embedding = embedding.squeeze()

            # Create Qdrant point
            points.append(
                PointStruct(
                    id=memory.id,
                    vector=embedding.tolist(),
                    payload={
                        "meeting_id": memory.meeting_id,
                        "content": memory.content,
                        "speaker": memory.speaker,
                        "timestamp": memory.timestamp,
                        "metadata": memory.metadata,
                        "entity_mentions": memory.entity_mentions,
                    },
                )
            )

            # Save to SQLite
            cursor.execute(
                """
                INSERT INTO memories 
                (id, meeting_id, content, speaker, timestamp, metadata, 
                 entity_mentions, embedding_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory.id,
                    memory.meeting_id,
                    memory.content,
                    memory.speaker,
                    memory.timestamp,
                    json.dumps(memory.metadata),
                    json.dumps(memory.entity_mentions),
                    memory.id,
                    memory.created_at.isoformat(),
                ),
            )

        # Upload to Qdrant
        self.qdrant.upsert(collection_name=self.collection_name, points=points)

        # Update meeting memory count
        if memories:
            cursor.execute(
                """
                UPDATE meetings 
                SET memory_count = memory_count + ?
                WHERE id = ?
            """,
                (len(memories), memories[0].meeting_id),
            )

        conn.commit()
        conn.close()

        return [m.id for m in memories]

    def search(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar memories."""
        # Build Qdrant filter if provided
        qdrant_filter = None
        if filters:
            must_conditions = []
            if "meeting_id" in filters:
                must_conditions.append(
                    {"key": "meeting_id", "match": {"value": filters["meeting_id"]}}
                )
            if "entity_mentions" in filters:
                for entity_id in filters["entity_mentions"]:
                    must_conditions.append(
                        {"key": "entity_mentions", "match": {"any": [entity_id]}}
                    )

            if must_conditions:
                qdrant_filter = {"must": must_conditions}

        # Ensure query_embedding is 1D
        if query_embedding.ndim > 1:
            query_embedding = query_embedding.squeeze()

        # Search in Qdrant
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit,
            query_filter=qdrant_filter,
        )

        if not results:
            return []

        # Get memory and meeting details from SQLite
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        search_results = []
        for result in results:
            # Get memory
            cursor.execute(
                """
                SELECT m.*, mt.title, mt.summary
                FROM memories m
                JOIN meetings mt ON m.meeting_id = mt.id
                WHERE m.id = ?
            """,
                (result.id,),
            )

            row = cursor.fetchone()
            if row:
                memory = Memory(
                    id=row[0],
                    meeting_id=row[1],
                    content=row[2],
                    speaker=row[3],
                    timestamp=row[4],
                    metadata=json.loads(row[5]) if row[5] else {},
                    entity_mentions=json.loads(row[6]) if row[6] else [],
                    embedding_id=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                )

                # Get mentioned entities
                relevant_entities = []
                if memory.entity_mentions:
                    # Create a new connection with row_factory for proper column access
                    entity_conn = sqlite3.connect(self.db_path)
                    entity_conn.row_factory = sqlite3.Row
                    entity_cursor = entity_conn.cursor()
                    
                    placeholders = ",".join("?" * len(memory.entity_mentions))
                    entity_cursor.execute(
                        f"""
                        SELECT * FROM entities 
                        WHERE id IN ({placeholders})
                    """,
                        memory.entity_mentions,
                    )

                    for entity_row in entity_cursor.fetchall():
                        relevant_entities.append(self._row_to_entity(entity_row))
                    
                    entity_conn.close()

                # Basic meeting info for context
                meeting = Meeting(id=row[1], title=row[9], summary=row[10])

                search_results.append(
                    SearchResult(
                        memory=memory,
                        meeting=meeting,
                        score=result.score,
                        distance=1.0 - result.score,
                        relevant_entities=relevant_entities,
                    )
                )

        conn.close()
        return search_results

    def get_meeting(self, meeting_id: str) -> Optional[Meeting]:
        """Get meeting by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM meetings WHERE id = ?
        """,
            (meeting_id,),
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            meeting = Meeting(
                id=row[0],
                title=row[1],
                transcript=row[2],
                participants=json.loads(row[3]) if row[3] else [],
                date=datetime.fromisoformat(row[4]) if row[4] else None,
                summary=row[5],
                topics=json.loads(row[6]) if row[6] else [],
                key_decisions=json.loads(row[7]) if row[7] else [],
                action_items=json.loads(row[8]) if row[8] else [],
                created_at=datetime.fromisoformat(row[9]),
                memory_count=row[10],
                entity_count=row[11],
            )
            
            # Handle new fields if they exist (backward compatibility)
            if len(row) > 12:
                meeting.email_metadata = json.loads(row[12]) if row[12] else None
                meeting.project_tags = json.loads(row[13]) if row[13] else []
                meeting.meeting_type = row[14]
                meeting.actual_start_time = datetime.fromisoformat(row[15]) if row[15] else None
                meeting.actual_end_time = datetime.fromisoformat(row[16]) if row[16] else None
                meeting.detailed_summary = row[17]
                meeting.raw_extraction = json.loads(row[18]) if row[18] else None
                meeting.organization_context = row[19]
            
            return meeting

        return None

    def get_all_meetings(self) -> List[Meeting]:
        """Get all meetings."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM meetings ORDER BY created_at DESC
        """
        )

        meetings = []
        for row in cursor.fetchall():
            meeting = Meeting(
                id=row[0],
                title=row[1],
                transcript=row[2],
                participants=json.loads(row[3]) if row[3] else [],
                date=datetime.fromisoformat(row[4]) if row[4] else None,
                summary=row[5],
                topics=json.loads(row[6]) if row[6] else [],
                key_decisions=json.loads(row[7]) if row[7] else [],
                action_items=json.loads(row[8]) if row[8] else [],
                created_at=datetime.fromisoformat(row[9]),
                memory_count=row[10],
                entity_count=row[11],
            )
            
            # Handle new fields if they exist (backward compatibility)
            if len(row) > 12:
                meeting.email_metadata = json.loads(row[12]) if row[12] else None
                meeting.project_tags = json.loads(row[13]) if row[13] else []
                meeting.meeting_type = row[14]
                meeting.actual_start_time = datetime.fromisoformat(row[15]) if row[15] else None
                meeting.actual_end_time = datetime.fromisoformat(row[16]) if row[16] else None
                meeting.detailed_summary = row[17]
                meeting.raw_extraction = json.loads(row[18]) if row[18] else None
                meeting.organization_context = row[19]
            
            meetings.append(meeting)

        conn.close()
        return meetings

    def get_memories_by_meeting(self, meeting_id: str) -> List[Memory]:
        """Get all memories for a meeting."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM memories 
            WHERE meeting_id = ?
            ORDER BY created_at
        """,
            (meeting_id,),
        )

        memories = []
        for row in cursor.fetchall():
            memories.append(
                Memory(
                    id=row[0],
                    meeting_id=row[1],
                    content=row[2],
                    speaker=row[3],
                    timestamp=row[4],
                    metadata=json.loads(row[5]) if row[5] else {},
                    entity_mentions=json.loads(row[6]) if row[6] else [],
                    embedding_id=row[7],
                    created_at=datetime.fromisoformat(row[8]),
                )
            )

        conn.close()
        return memories
    
    # BATCH OPERATIONS FOR PERFORMANCE
    def save_entities_batch(self, entities: List[Entity]) -> List[str]:
        """Save or update entities in batch for better performance."""
        if not entities:
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        saved_ids = []
        
        try:
            # First, check which entities already exist
            normalized_names_types = [(e.normalized_name, e.type) for e in entities]
            placeholders = ','.join(['(?, ?)'] * len(normalized_names_types))
            flat_values = [item for sublist in normalized_names_types for item in sublist]
            
            cursor.execute(f"""
                SELECT normalized_name, type, id, attributes
                FROM entities
                WHERE (normalized_name, type) IN ({placeholders})
            """, flat_values)
            
            existing_entities = {(row[0], row[1]): {'id': row[2], 'attrs': row[3]} 
                               for row in cursor.fetchall()}
            
            # Separate into updates and inserts
            updates = []
            inserts = []
            
            for entity in entities:
                key = (entity.normalized_name, entity.type)
                if key in existing_entities:
                    # Prepare update
                    entity_id = existing_entities[key]['id']
                    old_attrs = json.loads(existing_entities[key]['attrs']) if existing_entities[key]['attrs'] else {}
                    merged_attrs = {**old_attrs, **entity.attributes}
                    updates.append((json.dumps(merged_attrs), datetime.now().isoformat(), entity_id))
                    saved_ids.append(entity_id)
                else:
                    # Prepare insert
                    inserts.append((
                        entity.id,
                        entity.type,
                        entity.name,
                        entity.normalized_name,
                        json.dumps(entity.attributes),
                        entity.first_seen.isoformat(),
                        entity.last_updated.isoformat()
                    ))
                    saved_ids.append(entity.id)
            
            # Execute batch updates
            if updates:
                cursor.executemany("""
                    UPDATE entities 
                    SET attributes = ?, last_updated = ?
                    WHERE id = ?
                """, updates)
            
            # Execute batch inserts
            if inserts:
                cursor.executemany("""
                    INSERT INTO entities 
                    (id, type, name, normalized_name, attributes, first_seen, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, inserts)
            
            conn.commit()
        finally:
            conn.close()
        
        return saved_ids
    
    def save_transitions_batch(self, transitions: List[StateTransition]) -> None:
        """Save state transitions in batch for better performance."""
        if not transitions:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            data = [
                (
                    trans.id,
                    trans.entity_id,
                    json.dumps(trans.from_state) if trans.from_state else None,
                    json.dumps(trans.to_state),
                    json.dumps(trans.changed_fields),
                    trans.reason,
                    trans.meeting_id,
                    trans.timestamp.isoformat()
                )
                for trans in transitions
            ]
            
            cursor.executemany("""
                INSERT INTO state_transitions 
                (id, entity_id, from_state, to_state, changed_fields, 
                 reason, meeting_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            conn.commit()
        finally:
            conn.close()
    
    def get_entities_batch(self, entity_ids: List[str]) -> Dict[str, Entity]:
        """Get multiple entities by ID in a single query."""
        if not entity_ids:
            return {}
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            placeholders = ','.join(['?'] * len(entity_ids))
            cursor.execute(f"""
                SELECT * FROM entities
                WHERE id IN ({placeholders})
            """, entity_ids)
            
            entities = {}
            for row in cursor.fetchall():
                entity = self._row_to_entity(row)
                entities[entity.id] = entity
            
            return entities
        finally:
            conn.close()
    
    def search_memories(
        self, 
        query_embedding: np.ndarray,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20
    ) -> List[SearchResult]:
        """Search for similar memories using vector search."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        # Build Qdrant filters
        qdrant_filters = []
        if filters:
            for key, value in filters.items():
                qdrant_filters.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
        
        # Search in Qdrant
        search_filter = Filter(must=qdrant_filters) if qdrant_filters else None
        
        results = self.qdrant.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            filter=search_filter,
            limit=limit,
            with_payload=True
        )
        
        # Convert to SearchResult objects
        search_results = []
        for result in results:
            # Get the memory from database
            memory_id = result.payload.get("memory_id")
            if memory_id:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM memories WHERE id = ?",
                    (memory_id,)
                )
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    memory = Memory(
                        id=row[0],
                        meeting_id=row[1],
                        content=row[2],
                        speaker=row[3],
                        timestamp=row[4],
                        metadata=json.loads(row[5]) if row[5] else {},
                        entity_mentions=json.loads(row[6]) if row[6] else [],
                        embedding_id=row[7],
                        created_at=datetime.fromisoformat(row[8])
                    )
                    
                    search_results.append(SearchResult(
                        memory=memory,
                        score=result.score,
                        metadata=result.payload
                    ))
        
        return search_results
    
    def get_states_batch(self, entity_ids: List[str]) -> Dict[str, EntityState]:
        """Get the most recent state for multiple entities in a single query."""
        if not entity_ids:
            return {}
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get the most recent state for each entity
            placeholders = ','.join(['?'] * len(entity_ids))
            cursor.execute(f"""
                SELECT es1.*
                FROM entity_states es1
                INNER JOIN (
                    SELECT entity_id, MAX(timestamp) as max_timestamp
                    FROM entity_states
                    WHERE entity_id IN ({placeholders})
                    GROUP BY entity_id
                ) es2 ON es1.entity_id = es2.entity_id AND es1.timestamp = es2.max_timestamp
            """, entity_ids)
            
            states = {}
            for row in cursor.fetchall():
                state = EntityState(
                    id=row[0],
                    entity_id=row[1],
                    state=json.loads(row[2]) if row[2] else {},
                    meeting_id=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    confidence=row[5]
                )
                states[state.entity_id] = state
            
            return states
        finally:
            conn.close()
