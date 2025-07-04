"""
Meeting context extraction for consultant workstreams.
Identifies which workstream, team, and hierarchy level a meeting belongs to.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class MeetingContext:
    """Rich context about a meeting"""
    workstream: Optional[str] = None  # UAT, Hypercare, Standard Costing
    team: Optional[str] = None        # Finance, IT, Operations
    level: Optional[str] = None       # Strategic, Tactical, Operational
    meeting_series: Optional[str] = None  # Daily standup, Weekly review
    stakeholder_type: Optional[str] = None  # Client, Internal, Mixed


class MeetingContextExtractor:
    """Extract rich context from meeting titles and content."""
    
    # Workstream patterns
    WORKSTREAM_PATTERNS = {
        'uat': [
            r'uat\s+readiness', r'user\s+acceptance', r'uat\s+dashboard',
            r'uat\s+planning', r'uat\s+coordination', r'acceptance\s+testing'
        ],
        'hypercare': [
            r'hyper\s*care', r'post[\s-]?go[\s-]?live', r'stabilization',
            r'warranty\s+period', r'early\s+life\s+support'
        ],
        'standard_costing': [
            r'standard\s+cost', r'cost\s+model', r'costing\s+review',
            r'cost\s+analysis', r'standard\s+costing'
        ],
        'brv': [
            r'brv\s+readiness', r'business\s+readiness', r'brv\s+validation',
            r'readiness\s+assessment'
        ]
    }
    
    # Team patterns
    TEAM_PATTERNS = {
        'finance': [
            r'finance\s+team', r'financial', r'accounting', r'treasury',
            r'cost\s+center', r'budget'
        ],
        'it': [
            r'it\s+team', r'technology', r'systems', r'infrastructure',
            r'application', r'data\s+center'
        ],
        'operations': [
            r'operations', r'ops\s+team', r'supply\s+chain', r'logistics',
            r'manufacturing', r'production'
        ],
        'hr': [
            r'hr\s+team', r'human\s+resources', r'people\s+team', r'talent',
            r'organizational\s+change'
        ]
    }
    
    # Meeting level patterns
    LEVEL_PATTERNS = {
        'strategic': [
            r'steering', r'executive', r'leadership', r'strategy',
            r'portfolio', r'governance'
        ],
        'tactical': [
            r'planning', r'coordination', r'alignment', r'review',
            r'checkpoint', r'status'
        ],
        'operational': [
            r'daily', r'standup', r'working\s+session', r'deep\s+dive',
            r'troubleshooting', r'issue\s+resolution'
        ]
    }
    
    def extract_context(self, title: str, content: str, participants: List[str]) -> MeetingContext:
        """Extract comprehensive context from meeting information."""
        context = MeetingContext()
        
        # Normalize text for matching
        title_lower = title.lower()
        content_lower = content.lower()[:500]  # First 500 chars for efficiency
        
        # Extract workstream
        context.workstream = self._match_pattern(
            title_lower + " " + content_lower,
            self.WORKSTREAM_PATTERNS
        )
        
        # Extract team
        context.team = self._match_pattern(
            title_lower + " " + content_lower,
            self.TEAM_PATTERNS
        )
        
        # Extract level
        context.level = self._match_pattern(
            title_lower,
            self.LEVEL_PATTERNS
        )
        
        # Detect meeting series
        context.meeting_series = self._detect_series(title_lower)
        
        # Determine stakeholder type
        context.stakeholder_type = self._classify_stakeholders(participants)
        
        logger.info(f"Extracted context for '{title}': {context}")
        return context
    
    def _match_pattern(self, text: str, pattern_dict: Dict[str, List[str]]) -> Optional[str]:
        """Match text against pattern dictionary."""
        for category, patterns in pattern_dict.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        return None
    
    def _detect_series(self, title: str) -> Optional[str]:
        """Detect if meeting is part of a series."""
        series_patterns = {
            'daily_standup': r'daily\s+(standup|stand-up|sync|check-in)',
            'weekly_review': r'weekly\s+(review|status|update|sync)',
            'steering_committee': r'steering\s+(committee|comm|meeting)',
            'working_session': r'working\s+session|workshop',
            'checkpoint': r'checkpoint|check-in|touchpoint'
        }
        
        for series, pattern in series_patterns.items():
            if re.search(pattern, title, re.IGNORECASE):
                return series
        return None
    
    def _classify_stakeholders(self, participants: List[str]) -> str:
        """Classify meeting based on participants."""
        if not participants:
            return 'unknown'
        
        # Simple heuristic - could be enhanced with domain detection
        if any('@client.com' in p for p in participants):
            if any('@consultingfirm.com' in p for p in participants):
                return 'mixed'
            return 'client'
        return 'internal'
    
    def create_hierarchy_key(self, context: MeetingContext) -> str:
        """Create a hierarchical key for entity relationships."""
        parts = []
        
        if context.workstream:
            parts.append(context.workstream)
        if context.team:
            parts.append(context.team)
        if context.level:
            parts.append(context.level)
            
        return "/".join(parts) if parts else "general"


class WorkstreamAggregator:
    """Aggregate information across multiple meetings in a workstream."""
    
    def __init__(self):
        self.meeting_clusters = {}  # workstream -> list of meetings
        
    def add_meeting(self, meeting_id: str, context: MeetingContext, entities: List[str]):
        """Add a meeting to its workstream cluster."""
        if not context.workstream:
            context.workstream = 'general'
            
        if context.workstream not in self.meeting_clusters:
            self.meeting_clusters[context.workstream] = []
            
        self.meeting_clusters[context.workstream].append({
            'meeting_id': meeting_id,
            'context': context,
            'entities': entities,
            'timestamp': datetime.now()
        })
    
    def get_workstream_summary(self, workstream: str) -> Dict[str, Any]:
        """Get aggregated summary for a workstream."""
        if workstream not in self.meeting_clusters:
            return {}
            
        meetings = self.meeting_clusters[workstream]
        
        # Aggregate data
        all_entities = []
        teams_involved = set()
        levels = []
        
        for meeting in meetings:
            all_entities.extend(meeting['entities'])
            if meeting['context'].team:
                teams_involved.add(meeting['context'].team)
            if meeting['context'].level:
                levels.append(meeting['context'].level)
        
        # Count entity mentions
        entity_counts = {}
        for entity in all_entities:
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        
        # Determine workstream status based on meeting patterns
        strategic_meetings = sum(1 for l in levels if l == 'strategic')
        operational_meetings = sum(1 for l in levels if l == 'operational')
        
        if strategic_meetings > operational_meetings:
            phase = 'planning'
        else:
            phase = 'execution'
        
        return {
            'workstream': workstream,
            'total_meetings': len(meetings),
            'teams_involved': list(teams_involved),
            'key_entities': sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'phase': phase,
            'last_meeting': max(m['timestamp'] for m in meetings) if meetings else None
        }