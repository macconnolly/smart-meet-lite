"""
Consultant-specific query engine that understands workstreams, hierarchies, and synthesis.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from src.storage import MemoryStorage
from src.embeddings import EmbeddingEngine
from src.entity_resolver import EntityResolver
from src.meeting_synthesis import MeetingSynthesizer
from src.entity_hierarchy import EntityHierarchyManager
from src.models import BIQueryResult, QueryIntent

logger = logging.getLogger(__name__)


class ConsultantQueryEngine:
    """Query engine optimized for consultant use cases."""
    
    WORKSTREAM_ALIASES = {
        'uat': ['user acceptance testing', 'uat dashboard', 'acceptance testing'],
        'hypercare': ['hyper care', 'post go live', 'stabilization'],
        'standard_costing': ['standard cost', 'costing', 'cost model']
    }
    
    def __init__(
        self,
        storage: MemoryStorage,
        embeddings: EmbeddingEngine,
        entity_resolver: EntityResolver,
        synthesizer: MeetingSynthesizer,
        hierarchy_manager: EntityHierarchyManager
    ):
        self.storage = storage
        self.embeddings = embeddings
        self.entity_resolver = entity_resolver
        self.synthesizer = synthesizer
        self.hierarchy = hierarchy_manager
        
    def process_query(self, query: str) -> BIQueryResult:
        """Process consultant query with workstream awareness."""
        logger.info(f"Processing consultant query: {query}")
        
        # Detect workstream context
        workstream = self._detect_workstream(query)
        
        # Classify intent with consultant patterns
        intent = self._classify_consultant_intent(query, workstream)
        
        # Route to appropriate handler
        if intent.intent_type == 'workstream_status':
            return self._handle_workstream_status(query, workstream)
        elif intent.intent_type == 'cross_team':
            return self._handle_cross_team_query(query, workstream)
        elif intent.intent_type == 'synthesis':
            return self._handle_synthesis_query(query, workstream)
        elif intent.intent_type == 'hierarchy':
            return self._handle_hierarchy_query(query, intent)
        else:
            # Fall back to standard handling
            return self._handle_standard_query(query, intent)
    
    def _detect_workstream(self, query: str) -> Optional[str]:
        """Detect which workstream the query is about."""
        query_lower = query.lower()
        
        for workstream, aliases in self.WORKSTREAM_ALIASES.items():
            if workstream in query_lower:
                return workstream
            for alias in aliases:
                if alias in query_lower:
                    return workstream
        
        return None
    
    def _classify_consultant_intent(self, query: str, workstream: Optional[str]) -> QueryIntent:
        """Classify query intent with consultant-specific patterns."""
        query_lower = query.lower()
        
        # Workstream status patterns
        if any(phrase in query_lower for phrase in [
            'status of', 'how is', 'where are we with', 'update on'
        ]) and workstream:
            return QueryIntent(
                intent_type='workstream_status',
                entities=[workstream],
                filters={'workstream': workstream}
            )
        
        # Cross-team coordination patterns
        if any(phrase in query_lower for phrase in [
            'across teams', 'all teams', 'which teams', 'team coordination'
        ]):
            return QueryIntent(
                intent_type='cross_team',
                entities=[],
                filters={'workstream': workstream} if workstream else {}
            )
        
        # Synthesis patterns (your 30 meetings problem)
        if any(phrase in query_lower for phrase in [
            'today', 'this week', 'all meetings', 'summary of', 'what happened'
        ]):
            return QueryIntent(
                intent_type='synthesis',
                entities=[],
                filters={'workstream': workstream} if workstream else {}
            )
        
        # Hierarchy patterns
        if any(phrase in query_lower for phrase in [
            'breakdown', 'all tasks', 'subtasks', 'dependencies', 'tree'
        ]):
            return QueryIntent(
                intent_type='hierarchy',
                entities=self._extract_entities(query),
                filters={}
            )
        
        # Default classification
        return QueryIntent(intent_type='search', entities=[], filters={})
    
    def _handle_workstream_status(self, query: str, workstream: str) -> BIQueryResult:
        """Handle workstream status queries."""
        # Get synthesis for the workstream
        synthesis = self.synthesizer.synthesize_workstream_progress(
            workstream,
            time_window=timedelta(days=1)  # Today's meetings
        )
        
        # Build comprehensive answer
        answer_parts = [synthesis['executive_summary']]
        
        # Add specific insights
        if synthesis['state_changes']:
            answer_parts.append(f"\nRecent progress:")
            for change in synthesis['state_changes'][:5]:
                answer_parts.append(f"• {change['entity']}: {change['change']}")
        
        if synthesis['blockers']:
            answer_parts.append(f"\nCurrent blockers:")
            for blocker in synthesis['blockers'][:3]:
                answer_parts.append(f"• {blocker}")
        
        if synthesis['action_items']:
            answer_parts.append(f"\nAction items ({len(synthesis['action_items'])} total):")
            for item in synthesis['action_items'][:3]:
                assignee = item.get('assignee', 'Unassigned')
                answer_parts.append(f"• {item['task']} ({assignee})")
        
        answer = "\n".join(answer_parts)
        
        return BIQueryResult(
            query=query,
            intent=QueryIntent(
                intent_type='workstream_status',
                entities=[workstream],
                filters={'workstream': workstream}
            ),
            answer=answer,
            confidence=0.85,
            evidence=synthesis,
            metadata={
                'meeting_count': synthesis['meeting_count'],
                'teams_involved': list(synthesis['teams_involved'])
            }
        )
    
    def _handle_cross_team_query(self, query: str, workstream: Optional[str]) -> BIQueryResult:
        """Handle cross-team coordination queries."""
        # Get all teams involved in workstream
        if workstream:
            synthesis = self.synthesizer.synthesize_workstream_progress(workstream)
            teams = synthesis['teams_involved']
            
            # Get team-specific insights
            team_insights = []
            for team in teams:
                team_meetings = [m for m in synthesis.get('meetings', []) 
                               if m.get('context', {}).get('team') == team]
                
                team_insights.append({
                    'team': team,
                    'meeting_count': len(team_meetings),
                    'key_entities': self._get_team_entities(team, workstream)
                })
            
            answer = f"Cross-team coordination for {workstream}:\n\n"
            for insight in team_insights:
                answer += f"**{insight['team']} Team:**\n"
                answer += f"• Meetings: {insight['meeting_count']}\n"
                answer += f"• Focus areas: {', '.join(insight['key_entities'][:3])}\n\n"
            
            return BIQueryResult(
                query=query,
                intent=QueryIntent(intent_type='cross_team', entities=list(teams)),
                answer=answer,
                confidence=0.8,
                evidence={'team_insights': team_insights}
            )
        
        return BIQueryResult(
            query=query,
            intent=QueryIntent(intent_type='cross_team', entities=[]),
            answer="Please specify a workstream for cross-team analysis.",
            confidence=0.3
        )
    
    def _handle_synthesis_query(self, query: str, workstream: Optional[str]) -> BIQueryResult:
        """Handle synthesis queries (what happened today/this week)."""
        # Determine time window
        if 'today' in query.lower():
            time_window = timedelta(days=1)
        elif 'week' in query.lower():
            time_window = timedelta(days=7)
        else:
            time_window = timedelta(days=1)  # Default to today
        
        if workstream:
            synthesis = self.synthesizer.synthesize_workstream_progress(workstream, time_window)
        else:
            # Synthesize across all workstreams
            all_workstreams = ['uat', 'hypercare', 'standard_costing']
            synthesis_results = []
            
            for ws in all_workstreams:
                ws_synthesis = self.synthesizer.synthesize_workstream_progress(ws, time_window)
                if ws_synthesis['meeting_count'] > 0:
                    synthesis_results.append((ws, ws_synthesis))
            
            answer = f"Summary across all workstreams ({time_window.days} day(s)):\n\n"
            for ws, syn in synthesis_results:
                answer += f"**{ws.upper()}:**\n"
                answer += f"• Meetings: {syn['meeting_count']}\n"
                answer += f"• Teams: {', '.join(syn['teams_involved'])}\n"
                if syn['patterns']:
                    answer += f"• Key pattern: {syn['patterns'][0]}\n"
                answer += "\n"
            
            return BIQueryResult(
                query=query,
                intent=QueryIntent(intent_type='synthesis', entities=[]),
                answer=answer,
                confidence=0.9,
                evidence={'all_syntheses': synthesis_results}
            )
        
        return BIQueryResult(
            query=query,
            intent=QueryIntent(intent_type='synthesis', entities=[workstream] if workstream else []),
            answer=synthesis['executive_summary'],
            confidence=0.85,
            evidence=synthesis
        )
    
    def _handle_hierarchy_query(self, query: str, intent: QueryIntent) -> BIQueryResult:
        """Handle hierarchy/breakdown queries."""
        if not intent.entities:
            return BIQueryResult(
                query=query,
                intent=intent,
                answer="Please specify an entity to show the breakdown for.",
                confidence=0.3
            )
        
        # Get the main entity
        entity_name = intent.entities[0]
        entities = self.storage.search_entities(entity_name)
        
        if not entities:
            return BIQueryResult(
                query=query,
                intent=intent,
                answer=f"No entity found matching '{entity_name}'",
                confidence=0.2
            )
        
        entity = entities[0]
        
        # Get hierarchy tree
        tree = self.hierarchy.get_entity_tree(entity.id)
        
        # Format as readable tree
        answer = f"Hierarchy for {entity.name}:\n\n"
        answer += self._format_tree(tree)
        
        # Add related entities
        related = self.hierarchy.find_related_entities(entity.id)
        if related['parent']:
            answer += f"\nReports to: {related['parent'][0].name}"
        if related['sibling']:
            answer += f"\nPeer items: {', '.join([s.name for s in related['sibling'][:3]])}"
        
        return BIQueryResult(
            query=query,
            intent=intent,
            answer=answer,
            confidence=0.8,
            evidence={'tree': tree, 'related': related}
        )
    
    def _format_tree(self, node: Dict[str, Any], indent: int = 0) -> str:
        """Format hierarchy tree as indented text."""
        if not node:
            return ""
        
        lines = []
        prefix = "  " * indent + ("└─ " if indent > 0 else "")
        lines.append(f"{prefix}{node['name']} ({node['type']})")
        
        for child in node.get('children', []):
            lines.append(self._format_tree(child, indent + 1))
        
        return "\n".join(lines)
    
    def _extract_entities(self, query: str) -> List[str]:
        """Extract entity names from query."""
        # Simple implementation - could be enhanced
        # Look for quoted strings or capitalized words
        import re
        
        entities = []
        
        # Find quoted strings
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)
        
        # Find capitalized phrases (simple heuristic)
        words = query.split()
        i = 0
        while i < len(words):
            if words[i][0].isupper():
                phrase = [words[i]]
                j = i + 1
                while j < len(words) and words[j][0].isupper():
                    phrase.append(words[j])
                    j += 1
                if len(phrase) > 0:
                    entities.append(" ".join(phrase))
                i = j
            else:
                i += 1
        
        return entities
    
    def _get_team_entities(self, team: str, workstream: str) -> List[str]:
        """Get key entities for a team in a workstream."""
        # This would query the database for entities tagged with both team and workstream
        # Simplified for example
        return ["Task 1", "Task 2", "Task 3"]
    
    def _handle_standard_query(self, query: str, intent: QueryIntent) -> BIQueryResult:
        """Fallback to standard query handling."""
        # This would delegate to the original query engine
        return BIQueryResult(
            query=query,
            intent=intent,
            answer="Standard query processing not implemented in this example.",
            confidence=0.5
        )