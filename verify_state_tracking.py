#!/usr/bin/env python3
"""
Verify state tracking is working after ingestion.
Run this after the API has ingested some meetings.
"""

import sqlite3
import json
from datetime import datetime

def verify_state_tracking():
    """Check state tracking results."""
    conn = sqlite3.connect("data/memories.db")
    cursor = conn.cursor()
    
    print("=== STATE TRACKING VERIFICATION ===\n")
    
    # 1. Check meetings
    cursor.execute("SELECT COUNT(*) FROM meetings")
    meeting_count = cursor.fetchone()[0]
    print(f"✓ Meetings ingested: {meeting_count}")
    
    # 2. Check entities
    cursor.execute("SELECT COUNT(*) FROM entities")
    entity_count = cursor.fetchone()[0]
    print(f"✓ Entities extracted: {entity_count}")
    
    if entity_count == 0:
        print("\n❌ No entities found! State tracking cannot work without entities.")
        print("   The enhanced extractor may not be extracting entities properly.")
        
        # Check if raw extraction has entities
        cursor.execute("""
            SELECT m.title, m.raw_extraction 
            FROM meetings m 
            WHERE m.raw_extraction IS NOT NULL 
            LIMIT 1
        """)
        row = cursor.fetchone()
        if row:
            title, raw_extraction = row
            print(f"\n📋 Checking raw extraction from '{title}':")
            try:
                extraction = json.loads(raw_extraction)
                entities = extraction.get('entities', [])
                print(f"   - Raw entities in extraction: {len(entities)}")
                if entities:
                    print("   - Sample entity:", json.dumps(entities[0], indent=2))
            except:
                print("   - Could not parse raw extraction")
        
        conn.close()
        return
    
    # 3. Check entity states
    cursor.execute("SELECT COUNT(*) FROM entity_states")
    state_count = cursor.fetchone()[0]
    print(f"✓ Entity states recorded: {state_count}")
    
    # 4. Check state transitions
    cursor.execute("SELECT COUNT(*) FROM state_transitions")
    transition_count = cursor.fetchone()[0]
    print(f"✓ State transitions detected: {transition_count}")
    
    # 5. Show some examples
    print("\n📊 Sample Entity States:")
    cursor.execute("""
        SELECT e.name, e.type, es.state, es.confidence, m.title
        FROM entity_states es
        JOIN entities e ON es.entity_id = e.id
        JOIN meetings m ON es.meeting_id = m.id
        ORDER BY es.timestamp DESC
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        name, entity_type, state, confidence, meeting_title = row
        state_dict = json.loads(state) if state else {}
        print(f"\n  • {name} ({entity_type})")
        print(f"    State: {state_dict}")
        print(f"    Confidence: {confidence:.2f}")
        print(f"    Meeting: {meeting_title[:50]}...")
    
    if transition_count > 0:
        print("\n🔄 Sample State Transitions:")
        cursor.execute("""
            SELECT e.name, st.from_state, st.to_state, st.reason, m.title
            FROM state_transitions st
            JOIN entities e ON st.entity_id = e.id
            JOIN meetings m ON st.meeting_id = m.id
            ORDER BY st.timestamp DESC
            LIMIT 3
        """)
        
        for row in cursor.fetchall():
            name, from_state, to_state, reason, meeting_title = row
            from_dict = json.loads(from_state) if from_state else None
            to_dict = json.loads(to_state) if to_state else {}
            print(f"\n  • {name}")
            print(f"    From: {from_dict}")
            print(f"    To: {to_dict}")
            print(f"    Reason: {reason}")
            print(f"    Meeting: {meeting_title[:50]}...")
    else:
        print("\n⚠️  No state transitions detected!")
        print("   This means either:")
        print("   1. No entity changed states between meetings")
        print("   2. Post-processing is not working correctly")
        
        # Check if entities have multiple states
        cursor.execute("""
            SELECT e.name, COUNT(DISTINCT es.state) as state_count
            FROM entity_states es
            JOIN entities e ON es.entity_id = e.id
            GROUP BY e.id
            HAVING state_count > 1
            LIMIT 5
        """)
        
        multi_state_entities = cursor.fetchall()
        if multi_state_entities:
            print("\n   Found entities with multiple states:")
            for name, count in multi_state_entities:
                print(f"   - {name}: {count} different states")
            print("\n   ❌ Post-processing is NOT creating transitions!")
    
    # 6. Summary
    print("\n" + "="*50)
    if transition_count > 0:
        print("✅ State tracking is working!")
        print(f"   - {transition_count} transitions detected across {entity_count} entities")
    else:
        print("❌ State tracking is NOT working properly")
        print("   - No transitions detected despite having entities and states")
    
    conn.close()

if __name__ == "__main__":
    verify_state_tracking()