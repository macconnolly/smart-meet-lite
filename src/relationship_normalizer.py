"""Relationship type normalization utilities for consistent relationship storage."""

from typing import Optional
from src.models import RelationshipType

# Canonical relationship mappings
CANONICAL_RELATIONSHIPS = {
    # Ownership variants
    "owns": ["owns", "owner", "owned_by", "has_ownership"],
    
    # Work assignment variants
    "works_on": ["works_on", "working_on", "assigned", "assigned_to", "working"],
    "assigned_to": ["assigned_to", "assigned", "responsible", "tasked_with"],
    "responsible_for": ["responsible_for", "responsible", "accountable", "in_charge_of"],
    
    # Dependency variants
    "depends_on": ["depends_on", "depends", "dependent_on", "requires", "needs", "prerequisite", "reliant_on"],
    "blocks": ["blocks", "blocking", "blocker", "prevents", "impedes"],
    
    # Hierarchical variants
    "reports_to": ["reports_to", "reports", "managed_by", "supervised_by"],
    "includes": ["includes", "contains", "has", "comprises", "encompasses"],
    
    # Collaboration variants
    "collaborates_with": ["collaborates_with", "collaborates", "works_with", "partners_with", "teams_with"],
    
    # Generic variants
    "relates_to": ["relates_to", "related_to", "relates", "related", "connected_to", "associated_with"],
    "mentioned_in": ["mentioned_in", "mentioned", "referenced_in", "cited_in"]
}

# Build reverse mapping
RELATIONSHIP_MAPPING = {}
for canonical, variations in CANONICAL_RELATIONSHIPS.items():
    for variation in variations:
        RELATIONSHIP_MAPPING[variation.lower()] = canonical


def normalize_relationship_type(relationship: Optional[str]) -> str:
    """
    Normalize a relationship type to its canonical form.
    Returns a valid RelationshipType enum value.
    """
    if not relationship:
        return RelationshipType.RELATES_TO.value
    
    normalized = relationship.lower().strip().replace("-", "_").replace(" ", "_")
    
    # Check if it's already a valid enum value
    try:
        RelationshipType(normalized)
        return normalized
    except ValueError:
        pass
    
    # Try to map to canonical form
    canonical = RELATIONSHIP_MAPPING.get(normalized)
    if canonical:
        return canonical
    
    # Default to generic relationship
    return RelationshipType.RELATES_TO.value


def is_valid_relationship_type(relationship: str) -> bool:
    """Check if a relationship type is valid after normalization."""
    normalized = normalize_relationship_type(relationship)
    try:
        RelationshipType(normalized)
        return True
    except ValueError:
        return False