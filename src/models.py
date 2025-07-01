"""Enhanced data models for Smart-Meet Lite with business intelligence."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import uuid


# Entity types
class EntityType(str, Enum):
    PERSON = "person"
    PROJECT = "project"
    FEATURE = "feature"
    TASK = "task"
    DECISION = "decision"
    DEADLINE = "deadline"
    RISK = "risk"
    GOAL = "goal"
    METRIC = "metric"
    TEAM = "team"
    SYSTEM = "system"
    TECHNOLOGY = "technology"


# Relationship types
class RelationshipType(str, Enum):
    OWNS = "owns"
    WORKS_ON = "works_on"
    REPORTS_TO = "reports_to"
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    INCLUDES = "includes"
    ASSIGNED_TO = "assigned_to"
    RESPONSIBLE_FOR = "responsible_for"
    COLLABORATES_WITH = "collaborates_with"
    MENTIONED_IN = "mentioned_in"
    RELATES_TO = "relates_to"


@dataclass
class Entity:
    """A business entity extracted from meetings."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EntityType = EntityType.PERSON
    name: str = ""
    normalized_name: str = ""  # For matching across meetings
    attributes: Dict[str, Any] = field(default_factory=dict)
    first_seen: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)



@dataclass
class EntityMatch:
    """Represents a potential entity match with confidence score."""
    query_term: str
    entity: Optional['Entity'] = None
    confidence: float = 0.0
    match_type: str = ''  # 'exact', 'vector', 'fuzzy', 'llm'
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityState:
    """Current state of an entity at a point in time."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    meeting_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0


@dataclass
class EntityRelationship:
    """Relationship between two entities."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_entity_id: str = ""
    to_entity_id: str = ""
    relationship_type: RelationshipType = RelationshipType.RELATES_TO
    attributes: Dict[str, Any] = field(default_factory=dict)
    meeting_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    active: bool = True


@dataclass
class StateTransition:
    """A change in entity state."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    from_state: Optional[Dict[str, Any]] = None
    to_state: Dict[str, Any] = field(default_factory=dict)
    changed_fields: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    meeting_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Memory:
    """A memory extracted from a meeting."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str = ""
    content: str = ""
    speaker: Optional[str] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    entity_mentions: List[str] = field(default_factory=list)  # Entity IDs mentioned
    embedding_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Meeting:
    """A meeting with transcript and extracted intelligence."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    transcript: str = ""
    participants: List[str] = field(default_factory=list)
    date: Optional[datetime] = None
    summary: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    memory_count: int = 0
    entity_count: int = 0


@dataclass
class SearchResult:
    """Search result with score."""

    memory: Memory
    meeting: Optional[Meeting] = None
    score: float = 0.0
    distance: float = 0.0
    relevant_entities: List[Entity] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Enhanced result from LLM extraction."""

    memories: List[Memory]
    entities: List[Dict[str, Any]]  # Raw entity data from LLM
    relationships: List[Dict[str, Any]]  # Raw relationship data
    states: List[Dict[str, Any]]  # Current states of entities
    meeting_metadata: Dict[str, Any]
    summary: str
    topics: List[str]
    participants: List[str]
    decisions: List[str]
    action_items: List[Dict[str, Any]]


@dataclass
class QueryIntent:
    """Parsed intent from a user query."""

    intent_type: Literal[
        "status", "ownership", "timeline", "search", "relationship", "analytics"
    ]
    entities: List[str]  # Entity names/IDs to query
    filters: Dict[str, Any] = field(default_factory=dict)
    time_range: Optional[Dict[str, datetime]] = None
    aggregation: Optional[str] = None


@dataclass
class BIQueryResult:
    """Result from a business intelligence query."""

    query: str
    intent: QueryIntent
    answer: str
    supporting_data: List[Dict[str, Any]]
    entities_involved: List[Entity]
    confidence: float
    visualizations: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
