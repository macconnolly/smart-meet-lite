#!/usr/bin/env python3
"""Test state tracking functionality."""

import sqlite3
import json
from datetime import datetime

# Check if confidence column exists and state tracking works
conn = sqlite3.connect("data/memories.db")
cursor = conn.cursor()

print("Checking entity_states table schema:")
cursor.execute("PRAGMA table_info(entity_states)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

print("\nChecking if confidence column exists:")
confidence_exists = any(col[1] == 'confidence' for col in columns)
print(f"  Confidence column exists: {confidence_exists}")

# Try to insert a test state
try:
    test_id = f"test_{datetime.now().isoformat()}"
    cursor.execute("""
        INSERT INTO entity_states 
        (id, entity_id, state, meeting_id, timestamp, confidence)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        test_id,
        "test_entity_id",
        json.dumps({"status": "test"}),
        "test_meeting_id",
        datetime.now().isoformat(),
        0.95
    ))
    print("\n✓ Successfully inserted test state with confidence")
    
    # Clean up
    cursor.execute("DELETE FROM entity_states WHERE id = ?", (test_id,))
    conn.commit()
except Exception as e:
    print(f"\n✗ Failed to insert test state: {e}")

# Check actual entity states
cursor.execute("SELECT COUNT(*) FROM entity_states")
count = cursor.fetchone()[0]
print(f"\nTotal entity states in database: {count}")

if count > 0:
    cursor.execute("""
        SELECT e.name, es.state, es.confidence, es.timestamp 
        FROM entity_states es
        JOIN entities e ON es.entity_id = e.id
        ORDER BY es.timestamp DESC
        LIMIT 5
    """)
    print("\nRecent entity states:")
    for row in cursor.fetchall():
        state = json.loads(row[1])
        print(f"  - {row[0]}: {state.get('status', 'unknown')} (confidence: {row[2]}, time: {row[3]})")

conn.close()