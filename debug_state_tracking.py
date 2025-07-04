#!/usr/bin/env python3
"""Debug script to trace state tracking flow."""

import json
import sqlite3
from datetime import datetime

def trace_state_tracking():
    """Trace how state tracking works in the system."""
    
    # 1. Check recent meetings and their raw extractions
    conn = sqlite3.connect('data/memories.db')
    cursor = conn.cursor()
    
    print("=== RECENT MEETINGS WITH STATE DATA ===")
    cursor.execute("""
        SELECT id, title, raw_extraction, created_at
        FROM meetings
        WHERE raw_extraction IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    meetings_with_states = []
    for row in cursor.fetchall():
        meeting_id, title, raw_extraction, created_at = row
        data = json.loads(raw_extraction) if raw_extraction else {}
        
        # Count entities with current_state
        entities = data.get('entities', [])
        entities_with_state = [e for e in entities if 'current_state' in e and e['current_state']]
        
        print(f"\nMeeting: {title} ({meeting_id})")
        print(f"Created: {created_at}")
        print(f"Total entities: {len(entities)}")
        print(f"Entities with current_state: {len(entities_with_state)}")
        
        if entities_with_state:
            meetings_with_states.append((meeting_id, title, entities_with_state))
            for e in entities_with_state[:3]:  # Show first 3
                print(f"  - {e['name']}: {e['current_state']}")
    
    # 2. Check state transitions for these meetings
    print("\n=== STATE TRANSITIONS BY MEETING ===")
    for meeting_id, title, _ in meetings_with_states[:3]:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM state_transitions 
            WHERE meeting_id = ?
        """, (meeting_id,))
        
        transition_count = cursor.fetchone()[0]
        print(f"\n{title}: {transition_count} transitions")
        
        # Show details of transitions
        cursor.execute("""
            SELECT e.name, st.changed_fields, st.reason
            FROM state_transitions st
            JOIN entities e ON st.entity_id = e.id
            WHERE st.meeting_id = ?
            LIMIT 5
        """, (meeting_id,))
        
        for entity_name, changed_fields, reason in cursor.fetchall():
            fields = json.loads(changed_fields) if changed_fields else []
            print(f"  - {entity_name}: {fields} - {reason}")
    
    # 3. Check for entities without any state transitions
    print("\n=== ENTITIES WITHOUT STATE TRANSITIONS ===")
    cursor.execute("""
        SELECT e.name, e.type, e.first_seen
        FROM entities e
        LEFT JOIN state_transitions st ON e.id = st.entity_id
        WHERE st.id IS NULL
        ORDER BY e.first_seen DESC
        LIMIT 10
    """)
    
    for name, entity_type, first_seen in cursor.fetchall():
        print(f"  - {name} ({entity_type}) - First seen: {first_seen}")
    
    # 4. Check processor logic
    print("\n=== CHECKING PROCESSOR LOGIC ===")
    
    # Import and check which processor is used
    try:
        from src.api import processor
        processor_type = type(processor).__name__
        print(f"Processor type: {processor_type}")
        
        # Check if it has the right methods
        if hasattr(processor, 'process_meeting_with_context'):
            print("✓ Has process_meeting_with_context (async method)")
        if hasattr(processor, '_detect_implicit_state_changes'):
            print("✓ Has _detect_implicit_state_changes")
        if hasattr(processor, '_extract_current_states'):
            print("✓ Has _extract_current_states")
            
    except Exception as e:
        print(f"Error checking processor: {e}")
    
    # 5. Simulate what should happen
    print("\n=== SIMULATING STATE TRACKING ===")
    
    # Get a meeting with entities that have current_state
    if meetings_with_states:
        meeting_id, title, entities_with_state = meetings_with_states[0]
        
        print(f"\nFor meeting: {title}")
        print(f"Found {len(entities_with_state)} entities with current_state")
        
        # Check what transitions SHOULD be created
        for entity_data in entities_with_state[:3]:
            entity_name = entity_data['name']
            current_state = entity_data['current_state']
            
            # Find the entity in database
            cursor.execute("""
                SELECT id, normalized_name
                FROM entities
                WHERE normalized_name = ?
            """, (entity_name.lower().strip(),))
            
            entity_row = cursor.fetchone()
            if entity_row:
                entity_id, normalized_name = entity_row
                
                # Check prior state
                cursor.execute("""
                    SELECT state
                    FROM entity_states
                    WHERE entity_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (entity_id,))
                
                prior_row = cursor.fetchone()
                prior_state = json.loads(prior_row[0]) if prior_row else None
                
                print(f"\n  Entity: {entity_name}")
                print(f"    Prior state: {prior_state}")
                print(f"    Current state: {current_state}")
                
                # Check if transition exists
                cursor.execute("""
                    SELECT id, changed_fields
                    FROM state_transitions
                    WHERE entity_id = ? AND meeting_id = ?
                """, (entity_id, meeting_id))
                
                transition = cursor.fetchone()
                if transition:
                    print(f"    ✓ Transition exists: {json.loads(transition[1])}")
                else:
                    print(f"    ✗ NO TRANSITION FOUND!")
    
    conn.close()

if __name__ == "__main__":
    trace_state_tracking()