"""
Hierarchical entity management for complex project structures.
Handles parent-child relationships and context propagation.
"""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import uuid
from datetime import datetime
import logging

from src.models import Entity, EntityType, StateTransition
from src.storage import MemoryStorage

logger = logging.getLogger(__name__)


@dataclass
class HierarchicalEntity:
    """Entity with hierarchical relationships."""
    entity: Entity
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    hierarchy_level: int = 0  # 0=root, 1=project, 2=workstream, 3=task
    context_tags: Set[str] = field(default_factory=set)


class EntityHierarchyManager:
    """Manage hierarchical relationships between entities."""
    
    # Hierarchy rules for automatic parent-child inference
    HIERARCHY_RULES = {
        'project': {
            'can_parent': ['feature', 'milestone', 'deliverable', 'workstream'],
            'typical_parents': ['program', 'portfolio']
        },
        'workstream': {
            'can_parent': ['task', 'deliverable', 'milestone'],
            'typical_parents': ['project']
        },
        'task': {
            'can_parent': ['subtask'],
            'typical_parents': ['workstream', 'feature', 'milestone']
        },
        'person': {
            'can_parent': [],  # People don't have children entities
            'typical_parents': ['team', 'workstream']
        }
    }
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self._hierarchy_cache = {}  # entity_id -> HierarchicalEntity
        
    def create_or_update_hierarchy(
        self,
        entity: Entity,
        potential_parent_names: List[str],
        meeting_context: Dict[str, Any]
    ) -> HierarchicalEntity:
        """Create or update entity with hierarchical context."""
        
        # Get or create hierarchical wrapper
        if entity.id in self._hierarchy_cache:
            h_entity = self._hierarchy_cache[entity.id]
        else:
            h_entity = HierarchicalEntity(entity=entity)
            self._hierarchy_cache[entity.id] = h_entity
        
        # Try to find parent from potential names
        if not h_entity.parent_id and potential_parent_names:
            parent = self._find_best_parent(entity, potential_parent_names)
            if parent:
                self._set_parent(h_entity, parent)
        
        # Add context tags from meeting
        if meeting_context.get('workstream'):
            h_entity.context_tags.add(f"workstream:{meeting_context['workstream']}")
        if meeting_context.get('team'):
            h_entity.context_tags.add(f"team:{meeting_context['team']}")
            
        return h_entity
    
    def _find_best_parent(self, entity: Entity, potential_names: List[str]) -> Optional[Entity]:
        """Find the most likely parent entity from potential names."""
        rules = self.HIERARCHY_RULES.get(entity.type, {})
        typical_parents = rules.get('typical_parents', [])
        
        for name in potential_names:
            # Search for entities with matching names
            candidates = self.storage.search_entities(name)
            
            for candidate in candidates:
                # Check if this entity type can be a parent
                if candidate.type in typical_parents:
                    return candidate
                    
        return None
    
    def _set_parent(self, child: HierarchicalEntity, parent: Entity):
        """Set parent-child relationship."""
        child.parent_id = parent.id
        
        # Update parent's children
        if parent.id in self._hierarchy_cache:
            parent_h = self._hierarchy_cache[parent.id]
        else:
            parent_h = HierarchicalEntity(entity=parent)
            self._hierarchy_cache[parent.id] = parent_h
            
        if child.entity.id not in parent_h.children_ids:
            parent_h.children_ids.append(child.entity.id)
            
        # Update hierarchy levels
        child.hierarchy_level = parent_h.hierarchy_level + 1
        
        # Propagate context tags from parent
        child.context_tags.update(parent_h.context_tags)
        
        logger.info(f"Set hierarchy: {parent.name} -> {child.entity.name}")
    
    def propagate_state_change(
        self,
        entity_id: str,
        state_change: StateTransition,
        direction: str = 'both'
    ) -> List[Tuple[str, str]]:
        """
        Propagate state changes through hierarchy.
        Returns list of (entity_id, propagation_reason) tuples.
        """
        affected = []
        
        if entity_id not in self._hierarchy_cache:
            return affected
            
        h_entity = self._hierarchy_cache[entity_id]
        
        # Propagate up to parent
        if direction in ['up', 'both'] and h_entity.parent_id:
            parent = self._hierarchy_cache.get(h_entity.parent_id)
            if parent:
                reason = self._get_propagation_reason(state_change, 'up')
                if reason:
                    affected.append((h_entity.parent_id, reason))
        
        # Propagate down to children
        if direction in ['down', 'both']:
            for child_id in h_entity.children_ids:
                child = self._hierarchy_cache.get(child_id)
                if child:
                    reason = self._get_propagation_reason(state_change, 'down')
                    if reason:
                        affected.append((child_id, reason))
                        
        return affected
    
    def _get_propagation_reason(self, state_change: StateTransition, direction: str) -> Optional[str]:
        """Determine if and why a state change should propagate."""
        
        # Extract the actual state change
        if state_change.to_state.get('status') == 'blocked':
            if direction == 'up':
                return "Child entity is blocked"
            else:
                return "Parent entity is blocked - may affect this task"
                
        elif state_change.to_state.get('status') == 'completed':
            if direction == 'up':
                return "Child task completed - check if parent can progress"
                
        elif 'risk' in str(state_change.to_state).lower():
            return "Risk identified in related entity"
            
        return None
    
    def get_entity_tree(self, root_id: str, max_depth: int = 3) -> Dict[str, Any]:
        """Get full hierarchy tree for an entity."""
        if root_id not in self._hierarchy_cache:
            return {}
            
        def build_tree(entity_id: str, depth: int) -> Dict[str, Any]:
            if depth > max_depth:
                return None
                
            h_entity = self._hierarchy_cache.get(entity_id)
            if not h_entity:
                return None
                
            node = {
                'id': entity_id,
                'name': h_entity.entity.name,
                'type': h_entity.entity.type,
                'level': h_entity.hierarchy_level,
                'tags': list(h_entity.context_tags),
                'children': []
            }
            
            for child_id in h_entity.children_ids:
                child_node = build_tree(child_id, depth + 1)
                if child_node:
                    node['children'].append(child_node)
                    
            return node
            
        return build_tree(root_id, 0)
    
    def find_related_entities(
        self,
        entity_id: str,
        relationship_types: List[str] = ['parent', 'child', 'sibling']
    ) -> Dict[str, List[Entity]]:
        """Find all related entities in the hierarchy."""
        related = {'parent': [], 'child': [], 'sibling': []}
        
        if entity_id not in self._hierarchy_cache:
            return related
            
        h_entity = self._hierarchy_cache[entity_id]
        
        # Parent
        if 'parent' in relationship_types and h_entity.parent_id:
            parent = self._hierarchy_cache.get(h_entity.parent_id)
            if parent:
                related['parent'].append(parent.entity)
        
        # Children
        if 'child' in relationship_types:
            for child_id in h_entity.children_ids:
                child = self._hierarchy_cache.get(child_id)
                if child:
                    related['child'].append(child.entity)
        
        # Siblings (same parent)
        if 'sibling' in relationship_types and h_entity.parent_id:
            parent = self._hierarchy_cache.get(h_entity.parent_id)
            if parent:
                for sibling_id in parent.children_ids:
                    if sibling_id != entity_id:
                        sibling = self._hierarchy_cache.get(sibling_id)
                        if sibling:
                            related['sibling'].append(sibling.entity)
                            
        return related