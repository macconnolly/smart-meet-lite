"""State normalization utilities for consistent state storage."""

from typing import Dict, Any, Optional

# Canonical state values
CANONICAL_STATES = {
    "planned": ["planned", "planning", "not_started", "notstarted", "not started"],
    "in_progress": ["in_progress", "inprogress", "in progress", "in-progress", "in_process", "active", "ongoing"],
    "completed": ["completed", "complete", "done", "finished", "closed"],
    "blocked": ["blocked", "on_hold", "onhold", "on hold", "paused", "stuck"],
    "cancelled": ["cancelled", "canceled", "abandoned", "stopped"]
}

# Build reverse mapping
STATE_MAPPING = {}
for canonical, variations in CANONICAL_STATES.items():
    for variation in variations:
        STATE_MAPPING[variation.lower()] = canonical


def normalize_state_value(state: Optional[str]) -> Optional[str]:
    """Normalize a state value to its canonical form."""
    if not state:
        return state
    
    normalized = state.lower().strip()
    return STATE_MAPPING.get(normalized, normalized)


def normalize_state_dict(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize state values in a state dictionary."""
    if not state_dict:
        return state_dict
    
    normalized = state_dict.copy()
    
    # Normalize status field
    if 'status' in normalized and normalized['status']:
        normalized['status'] = normalize_state_value(normalized['status'])
    
    # Normalize progress field (ensure consistent format)
    if 'progress' in normalized and normalized['progress']:
        progress = str(normalized['progress']).strip()
        # Remove "complete" or "%" if present
        progress = progress.replace('complete', '').replace('%', '').strip()
        # Ensure it's a percentage
        if progress.isdigit():
            normalized['progress'] = f"{progress}%"
    
    return normalized


def denormalize_for_display(state_value: str) -> str:
    """Convert canonical state to display format."""
    display_map = {
        "planned": "Planned",
        "in_progress": "In Progress",
        "completed": "Completed",
        "blocked": "Blocked",
        "cancelled": "Cancelled"
    }
    return display_map.get(state_value, state_value.replace('_', ' ').title())