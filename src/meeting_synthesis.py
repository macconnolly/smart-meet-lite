"""
Meeting synthesis for multi-stakeholder project tracking.
Aggregates insights across multiple related meetings.
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from src.models import Meeting, Entity, StateTransition
from src.storage import MemoryStorage
from src.meeting_context import MeetingContext

logger = logging.getLogger(__name__)


class MeetingSynthesizer:
    """Synthesize insights across multiple related meetings."""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        
    def synthesize_workstream_progress(
        self,
        workstream: str,
        time_window: timedelta = timedelta(days=1)
    ) -> Dict[str, Any]:
        """
        Synthesize all meetings for a workstream within time window.
        Perfect for "What happened with UAT today across all teams?"
        """
        end_time = datetime.now()
        start_time = end_time - time_window
        
        # Get all meetings in time window
        meetings = self.storage.get_meetings_by_timerange(start_time, end_time)
        
        # Filter to workstream
        workstream_meetings = []
        for meeting in meetings:
            # Check if meeting is tagged with this workstream
            if hasattr(meeting, 'context') and meeting.context.get('workstream') == workstream:
                workstream_meetings.append(meeting)
        
        if not workstream_meetings:
            return {
                'workstream': workstream,
                'status': 'No meetings found',
                'time_window': str(time_window)
            }
        
        # Aggregate data
        synthesis = {
            'workstream': workstream,
            'time_window': str(time_window),
            'meeting_count': len(workstream_meetings),
            'teams_involved': set(),
            'key_decisions': [],
            'blockers': [],
            'progress_updates': [],
            'action_items': [],
            'entities_discussed': defaultdict(int),
            'state_changes': [],
            'overall_sentiment': None
        }
        
        # Process each meeting
        for meeting in workstream_meetings:
            # Add team
            if hasattr(meeting, 'context') and meeting.context.get('team'):
                synthesis['teams_involved'].add(meeting.context['team'])
            
            # Aggregate decisions
            if meeting.key_decisions:
                for decision in meeting.key_decisions:
                    synthesis['key_decisions'].append({
                        'decision': decision,
                        'meeting': meeting.title,
                        'date': meeting.date
                    })
            
            # Aggregate action items
            if meeting.action_items:
                for item in meeting.action_items:
                    synthesis['action_items'].append({
                        **item,
                        'meeting': meeting.title,
                        'date': meeting.date
                    })
            
            # Count entity mentions
            entities = self.storage.get_entities_by_meeting(meeting.id)
            for entity in entities:
                synthesis['entities_discussed'][entity.name] += 1
            
            # Get state changes
            transitions = self.storage.get_transitions_by_meeting(meeting.id)
            for transition in transitions:
                entity = self.storage.get_entity(transition.entity_id)
                synthesis['state_changes'].append({
                    'entity': entity.name if entity else transition.entity_id,
                    'change': self._describe_transition(transition),
                    'meeting': meeting.title
                })
        
        # Identify patterns
        synthesis['patterns'] = self._identify_patterns(synthesis)
        
        # Generate executive summary
        synthesis['executive_summary'] = self._generate_summary(synthesis)
        
        return synthesis
    
    def find_related_meetings(
        self,
        reference_meeting_id: str,
        lookback_days: int = 7
    ) -> List[Tuple[Meeting, float]]:
        """
        Find meetings related to a reference meeting.
        Returns list of (meeting, relevance_score) tuples.
        """
        reference = self.storage.get_meeting(reference_meeting_id)
        if not reference:
            return []
        
        # Get entities from reference meeting
        ref_entities = self.storage.get_entities_by_meeting(reference_meeting_id)
        ref_entity_ids = {e.id for e in ref_entities}
        
        # Get recent meetings
        end_time = reference.date or datetime.now()
        start_time = end_time - timedelta(days=lookback_days)
        recent_meetings = self.storage.get_meetings_by_timerange(start_time, end_time)
        
        related = []
        for meeting in recent_meetings:
            if meeting.id == reference_meeting_id:
                continue
                
            # Calculate relevance score
            score = self._calculate_relevance(reference, meeting, ref_entity_ids)
            if score > 0.3:  # Threshold for relevance
                related.append((meeting, score))
        
        # Sort by relevance
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:10]  # Top 10 related meetings
    
    def _calculate_relevance(
        self,
        ref_meeting: Meeting,
        candidate: Meeting,
        ref_entity_ids: Set[str]
    ) -> float:
        """Calculate relevance score between two meetings."""
        score = 0.0
        
        # Entity overlap
        candidate_entities = self.storage.get_entities_by_meeting(candidate.id)
        candidate_entity_ids = {e.id for e in candidate_entities}
        
        overlap = ref_entity_ids.intersection(candidate_entity_ids)
        if overlap:
            score += len(overlap) / len(ref_entity_ids) * 0.5
        
        # Context similarity
        if hasattr(ref_meeting, 'context') and hasattr(candidate, 'context'):
            if ref_meeting.context.get('workstream') == candidate.context.get('workstream'):
                score += 0.3
            if ref_meeting.context.get('team') == candidate.context.get('team'):
                score += 0.2
        
        # Time proximity (decay factor)
        if ref_meeting.date and candidate.date:
            days_apart = abs((ref_meeting.date - candidate.date).days)
            time_factor = max(0, 1 - (days_apart / 7))  # Linear decay over 7 days
            score *= (0.5 + 0.5 * time_factor)  # At least 50% score retained
        
        return score
    
    def _identify_patterns(self, synthesis: Dict[str, Any]) -> List[str]:
        """Identify patterns in synthesized data."""
        patterns = []
        
        # Check for blocker patterns
        blocker_count = len([sc for sc in synthesis['state_changes'] 
                            if 'blocked' in sc['change'].lower()])
        if blocker_count > 2:
            patterns.append(f"Multiple blockers identified ({blocker_count} items)")
        
        # Check for cross-team dependencies
        if len(synthesis['teams_involved']) > 2:
            patterns.append(f"High cross-team coordination ({len(synthesis['teams_involved'])} teams)")
        
        # Check for decision velocity
        if synthesis['meeting_count'] > 5 and len(synthesis['key_decisions']) < 2:
            patterns.append("Low decision velocity despite high meeting frequency")
        
        # Check for recurring entities
        top_entities = sorted(
            synthesis['entities_discussed'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        if top_entities and top_entities[0][1] > 5:
            patterns.append(f"Heavy focus on {top_entities[0][0]} ({top_entities[0][1]} mentions)")
        
        return patterns
    
    def _describe_transition(self, transition: StateTransition) -> str:
        """Generate human-readable description of state transition."""
        if not transition.from_state:
            return f"Initial state: {transition.to_state.get('status', 'unknown')}"
        
        from_status = transition.from_state.get('status', 'unknown')
        to_status = transition.to_state.get('status', 'unknown')
        
        if from_status != to_status:
            return f"{from_status} → {to_status}"
        
        # Look for other changes
        if transition.changed_fields:
            return f"Updated: {', '.join(transition.changed_fields)}"
        
        return "State updated"
    
    def _generate_summary(self, synthesis: Dict[str, Any]) -> str:
        """Generate executive summary of synthesis."""
        lines = []
        
        # Opening
        lines.append(
            f"Synthesis of {synthesis['meeting_count']} meetings for "
            f"{synthesis['workstream']} workstream in {synthesis['time_window']}:"
        )
        
        # Teams
        if synthesis['teams_involved']:
            teams = ', '.join(sorted(synthesis['teams_involved']))
            lines.append(f"• Teams involved: {teams}")
        
        # Key outcomes
        if synthesis['key_decisions']:
            lines.append(f"• Key decisions made: {len(synthesis['key_decisions'])}")
        
        if synthesis['blockers']:
            lines.append(f"• Blockers identified: {len(synthesis['blockers'])}")
        
        if synthesis['action_items']:
            lines.append(f"• Action items created: {len(synthesis['action_items'])}")
        
        # State changes
        if synthesis['state_changes']:
            completed = len([sc for sc in synthesis['state_changes'] 
                           if 'completed' in sc['change'].lower()])
            blocked = len([sc for sc in synthesis['state_changes'] 
                         if 'blocked' in sc['change'].lower()])
            
            if completed:
                lines.append(f"• Items completed: {completed}")
            if blocked:
                lines.append(f"• Items blocked: {blocked}")
        
        # Patterns
        if synthesis['patterns']:
            lines.append("\nKey patterns:")
            for pattern in synthesis['patterns']:
                lines.append(f"• {pattern}")
        
        return "\n".join(lines)