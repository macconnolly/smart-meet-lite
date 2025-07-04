"""
Enhanced hierarchical models for consulting intelligence.
Designed to handle complex program/workstream/team relationships.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Literal
import uuid


class EntityType(Enum):
    """Extended entity types for consulting context."""
    # Hierarchical levels
    PROGRAM = "program"              # Top-level initiative (e.g., "Enterprise Transformation")
    WORKSTREAM = "workstream"        # Major work track (e.g., "UAT Readiness")
    PROJECT = "project"              # Specific project within workstream
    DELIVERABLE = "deliverable"      # Concrete output (e.g., "UAT Dashboard")
    
    # Organizational
    PERSON = "person"
    TEAM = "team"                    # Functional team (e.g., "Finance UAT Team")
    CLIENT_ORG = "client_org"        # Client organization
    VENDOR = "vendor"                # Third-party vendor
    
    # Work items
    MILESTONE = "milestone"          # Key dates/checkpoints
    DECISION = "decision"            # Recorded decisions
    RISK = "risk"                    # Identified risks
    BLOCKER = "blocker"              # Current blockers
    DEPENDENCY = "dependency"        # Cross-team dependencies
    
    # Technical
    SYSTEM = "system"                # IT systems
    FEATURE = "feature"              # System features
    TASK = "task"                    # Specific tasks
    DEADLINE = "deadline"            # Hard deadlines


class RelationshipType(Enum):
    """Enhanced relationship types for complex org structures."""
    # Hierarchical
    PART_OF = "part_of"              # Workstream part of Program
    CONTAINS = "contains"            # Program contains Workstreams
    PARENT = "parent"                # Parent entity
    CHILD = "child"                  # Child entity
    
    # Ownership
    OWNS = "owns"                    # Direct ownership
    LEADS = "leads"                  # Leadership role
    SPONSORS = "sponsors"            # Executive sponsorship
    ACCOUNTABLE = "accountable"      # RACI - Accountable
    RESPONSIBLE = "responsible"      # RACI - Responsible
    CONSULTED = "consulted"          # RACI - Consulted
    INFORMED = "informed"            # RACI - Informed
    
    # Collaboration
    CONTRIBUTES_TO = "contributes_to"
    DEPENDS_ON = "depends_on"
    BLOCKS = "blocks"
    SUPPORTS = "supports"
    ESCALATES_TO = "escalates_to"
    
    # Temporal
    PRECEDES = "precedes"
    FOLLOWS = "follows"
    CONCURRENT_WITH = "concurrent_with"


class MeetingType(Enum):
    """Types of meetings in consulting context."""
    STEERING = "steering"            # Executive/steering committee
    PROGRAM = "program"              # Program-level sync
    WORKSTREAM = "workstream"        # Workstream coordination
    FUNCTIONAL = "functional"        # Functional team meeting
    WORKING = "working"              # Working session
    ONE_ON_ONE = "1:1"              # Individual sync
    INTERNAL = "internal"            # Consultant-only
    CLIENT = "client"                # Client-facing
    VENDOR = "vendor"                # Vendor meeting
    STANDUP = "standup"              # Daily standup
    REVIEW = "review"                # Review/checkpoint
    PLANNING = "planning"            # Planning session
    RETROSPECTIVE = "retrospective"  # Retro/lessons learned


class ParticipantRole(Enum):
    """Roles of meeting participants."""
    CONSULTANT = "consultant"        # Our team
    CLIENT = "client"                # Client team
    VENDOR = "vendor"                # Third party
    EXECUTIVE = "executive"          # C-level
    MANAGER = "manager"              # Middle management
    CONTRIBUTOR = "contributor"      # Individual contributor
    OBSERVER = "observer"            # Just observing


@dataclass
class HierarchicalEntity:
    """Entity with hierarchical awareness."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EntityType = EntityType.PROJECT
    name: str = ""
    normalized_name: str = ""
    
    # Hierarchical placement
    hierarchy_level: int = 0         # 0=Program, 1=Workstream, 2=Project, etc.
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    
    # Context
    program_id: Optional[str] = None    # Always know which program
    workstream_id: Optional[str] = None # Which workstream if applicable
    
    # Enhanced attributes
    attributes: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    # Ownership & responsibility
    owner_id: Optional[str] = None
    accountable_ids: List[str] = field(default_factory=list)
    responsible_ids: List[str] = field(default_factory=list)
    
    # State & status
    current_state: Dict[str, Any] = field(default_factory=dict)
    health_status: Literal["green", "yellow", "red", "unknown"] = "unknown"
    confidence_level: float = 0.0
    
    # Temporal
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Meeting associations
    discussed_in_meetings: Set[str] = field(default_factory=set)
    last_discussed: Optional[datetime] = None
    discussion_frequency: int = 0    # How often discussed


@dataclass
class EnhancedRelationship:
    """Relationship with richer context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_entity_id: str = ""
    to_entity_id: str = ""
    relationship_type: RelationshipType = RelationshipType.RELATED
    
    # Relationship strength and confidence
    strength: float = 1.0            # How strong is this relationship
    confidence: float = 1.0          # How confident are we
    
    # Temporal aspects
    established_date: datetime = field(default_factory=datetime.now)
    last_confirmed: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    # Context
    established_in_meeting: Optional[str] = None
    confirmed_in_meetings: Set[str] = field(default_factory=set)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeetingContext:
    """Rich context about a meeting."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meeting_id: str = ""
    
    # Meeting classification
    meeting_type: MeetingType = MeetingType.WORKING
    hierarchy_level: Literal["program", "workstream", "team", "individual"] = "team"
    
    # What program/workstream is this about?
    program_id: Optional[str] = None
    workstream_ids: List[str] = field(default_factory=list)
    primary_focus_entity_id: Optional[str] = None
    
    # Participants and their roles
    participants: Dict[str, ParticipantRole] = field(default_factory=dict)
    facilitator_id: Optional[str] = None
    decision_makers: List[str] = field(default_factory=list)
    
    # Meeting outcomes
    decisions_made: List[str] = field(default_factory=list)
    risks_identified: List[str] = field(default_factory=list)
    blockers_raised: List[str] = field(default_factory=list)
    
    # Follow-up
    follow_up_required: bool = False
    next_meeting_date: Optional[datetime] = None
    escalations_needed: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class StateTransitionEnhanced:
    """Enhanced state transition with context."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str = ""
    
    # State change details
    from_state: Optional[Dict[str, Any]] = None
    to_state: Dict[str, Any] = field(default_factory=dict)
    changed_fields: List[str] = field(default_factory=list)
    
    # Change classification
    change_type: Literal["progress", "status", "blocker", "assignment", "scope", "risk"] = "status"
    severity: Literal["minor", "major", "critical"] = "minor"
    
    # Context
    triggered_by_meeting_id: str = ""
    reason: str = ""
    
    # Impact analysis
    impacts_entities: List[str] = field(default_factory=list)  # Other affected entities
    cascading_changes: List[str] = field(default_factory=list)  # Triggered transitions
    
    # Confidence
    confidence: float = 1.0
    verified: bool = False
    
    # Temporal
    timestamp: datetime = field(default_factory=datetime.now)
    effective_date: Optional[datetime] = None  # When change actually takes effect


@dataclass
class WorkstreamStatus:
    """Aggregated status for a workstream."""
    workstream_id: str = ""
    workstream_name: str = ""
    
    # Overall health
    overall_status: Literal["on_track", "at_risk", "off_track", "blocked"] = "on_track"
    health_score: float = 0.0  # 0-100
    confidence: float = 0.0
    
    # Progress tracking
    completion_percentage: float = 0.0
    velocity_trend: Literal["accelerating", "steady", "slowing", "stalled"] = "steady"
    
    # Team readiness
    teams_ready: Dict[str, bool] = field(default_factory=dict)
    overall_readiness: float = 0.0
    
    # Blockers and risks
    active_blockers: List[Dict[str, Any]] = field(default_factory=list)
    active_risks: List[Dict[str, Any]] = field(default_factory=list)
    
    # Key dates
    planned_start: Optional[datetime] = None
    actual_start: Optional[datetime] = None
    target_completion: Optional[datetime] = None
    projected_completion: Optional[datetime] = None
    
    # Meeting activity
    last_discussed: Optional[datetime] = None
    discussion_frequency_week: int = 0
    teams_reporting: Set[str] = field(default_factory=set)
    
    # Synthesis metadata
    synthesized_from_meetings: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ConsultingContext:
    """Overall consulting engagement context."""
    client_name: str = ""
    engagement_type: str = ""  # e.g., "Digital Transformation"
    
    # Key programs
    active_programs: Dict[str, str] = field(default_factory=dict)  # id -> name
    
    # Team structure
    consulting_team: Dict[str, str] = field(default_factory=dict)  # id -> role
    client_stakeholders: Dict[str, str] = field(default_factory=dict)  # id -> role
    
    # Engagement timeline
    start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    key_milestones: List[Dict[str, Any]] = field(default_factory=list)
    
    # Current focus areas
    priority_workstreams: List[str] = field(default_factory=list)
    escalation_items: List[Dict[str, Any]] = field(default_factory=list)
    
    # Meeting patterns
    regular_meetings: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # Pattern analysis
    
    
@dataclass
class MeetingSynthesis:
    """Synthesis across multiple meetings."""
    topic: str = ""  # e.g., "UAT Readiness"
    entity_id: Optional[str] = None
    
    # Meetings included
    meeting_ids: List[str] = field(default_factory=list)
    meeting_count: int = 0
    date_range: Optional[tuple[datetime, datetime]] = None
    
    # Synthesized state
    current_state: Dict[str, Any] = field(default_factory=dict)
    consensus_status: Optional[str] = None
    
    # Conflicts detected
    conflicting_information: List[Dict[str, Any]] = field(default_factory=list)
    
    # Aggregated insights
    common_themes: List[str] = field(default_factory=list)
    recurring_blockers: List[str] = field(default_factory=list)
    
    # Team perspectives
    team_perspectives: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Actions and decisions
    all_action_items: List[Dict[str, Any]] = field(default_factory=list)
    key_decisions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Confidence
    synthesis_confidence: float = 0.0
    data_completeness: float = 0.0