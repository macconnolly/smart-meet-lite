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
                entity_count INTEGER DEFAULT 0
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
                last_updated TIMESTAMP NOT NULL,
                name_embedding BLOB,
                embedding_model VARCHAR(100),
                embedding_generated_at TIMESTAMP
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

        conn.commit()
        conn.close()

    def _row_to_entity(self, row: sqlite3.Row) -> Entity:
        """Convert a database row to an Entity object.
        
        Handles sqlite3.Row objects properly and deals with potentially missing columns
        for backward compatibility.
        """
        import logging
        
        # Handle embedding deserialization
        embedding = None
        if 'name_embedding' in row.keys() and row['name_embedding']:
            try:
                embedding = np.frombuffer(row['name_embedding'], dtype=np.float32)
            except Exception as e:
                logging.warning(f"Failed to deserialize embedding for entity {row['id']}: {e}")
        
        # Handle optional columns that might not exist in older databases
        embedding_model = None
        embedding_generated_at = None
        
        if 'embedding_model' in row.keys():
            embedding_model = row['embedding_model']
        
        if 'embedding_generated_at' in row.keys() and row['embedding_generated_at']:
            embedding_generated_at = datetime.fromisoformat(row['embedding_generated_at'])
        
        return Entity(
            id=row['id'],
            type=EntityType(row['type']),
            name=row['name'],
            normalized_name=row['normalized_name'],
            attributes=json.loads(row['attributes']) if row['attributes'] else {},
            first_seen=datetime.fromisoformat(row['first_seen']),
            last_updated=datetime.fromisoformat(row['last_updated']),
            # Extended attributes
            name_embedding=embedding,
            embedding_model=embedding_model,
            embedding_generated_at=embedding_generated_at
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

    def save_meeting(self, meeting: Meeting) -> str:
        """Save meeting to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO meetings 
            (id, title, transcript, participants, date, summary, topics, 
             key_decisions, action_items, created_at, memory_count, entity_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

    def update_entity_embedding(self, 
                              entity_id: str, 
                              embedding: np.ndarray,
                              model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Update entity name embedding for vector search."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE entities 
            SET name_embedding = ?, 
                embedding_model = ?,
                embedding_generated_at = ?
            WHERE id = ?
        """, (
            embedding.tobytes(),
            model_name,
            datetime.now().isoformat(),
            entity_id
        ))
        
        conn.commit()
        conn.close()

    def get_entities_needing_embeddings(self, limit: int = 100) -> List[Entity]:
        """Get entities that don't have embeddings yet."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM entities 
            WHERE name_embedding IS NULL 
            ORDER BY last_updated DESC
            LIMIT ?
        """, (limit,))
        
        entities = []
        for row in cursor.fetchall():
            entities.append(self._row_to_entity(row))
        
        conn.close()
        return entities

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
            return Meeting(
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
            meetings.append(
                Meeting(
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
            )

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
