#!/usr/bin/env python3
"""
One-time migration script to normalize all existing entity states.
Run this ONCE after implementing state normalization.
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.state_normalizer import normalize_state_dict

def migrate():
    """Migrate all entity states to normalized format."""
    print(f"Starting state normalization migration at {datetime.now()}")
    
    # Get database path from settings
    from src.config import settings
    db_path = settings.database_path
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create backup table
    print("Creating backup table...")
    cursor.execute("DROP TABLE IF EXISTS entity_states_backup")
    cursor.execute("""
        CREATE TABLE entity_states_backup AS 
        SELECT * FROM entity_states
    """)
    conn.commit()
    
    # Get all entity states
    print("Fetching all entity states...")
    cursor.execute("SELECT id, state FROM entity_states")
    rows = cursor.fetchall()
    print(f"Found {len(rows)} entity states to process")
    
    # Track changes
    updates = []
    changes_made = 0
    
    for state_id, state_json in rows:
        try:
            state = json.loads(state_json)
            original_state = json.dumps(state, sort_keys=True)
            
            # Normalize the state
            normalized = normalize_state_dict(state)
            
            # Check if anything changed
            new_state = json.dumps(normalized, sort_keys=True)
            if original_state != new_state:
                updates.append((new_state, state_id))
                changes_made += 1
                print(f"  Normalizing state {state_id}")
                
        except Exception as e:
            print(f"Error processing state {state_id}: {e}")
            continue
    
    # Apply updates
    if updates:
        print(f"\nApplying {changes_made} normalizations...")
        cursor.executemany("UPDATE entity_states SET state = ? WHERE id = ?", updates)
        conn.commit()
        print(f"✓ Updated {changes_made} states")
    else:
        print("✓ No states needed normalization")
    
    # Verify migration
    print("\nVerifying migration...")
    cursor.execute("""
        SELECT DISTINCT json_extract(state, '$.status') as status 
        FROM entity_states 
        WHERE json_extract(state, '$.status') IS NOT NULL
    """)
    statuses = [row[0] for row in cursor.fetchall()]
    print(f"Unique statuses after migration: {statuses}")
    
    conn.close()
    print(f"\nMigration completed at {datetime.now()}")

if __name__ == "__main__":
    # Safety check
    response = input("This will modify the database. Create a backup first! Continue? (yes/no): ")
    if response.lower() == 'yes':
        migrate()
    else:
        print("Migration cancelled.")