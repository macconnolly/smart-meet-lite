#!/usr/bin/env python3
"""Clean reset - Delete all data from both SQLite and Qdrant."""

import sqlite3
import os
import sys
from qdrant_client import QdrantClient
from datetime import datetime

# Add project root to path
sys.path.append('.')
from src.config import settings

def confirm_reset():
    """Ask for confirmation before resetting."""
    print("=" * 60)
    print("CLEAN RESET - THIS WILL DELETE ALL DATA")
    print("=" * 60)
    print("\nThis will delete:")
    print("- All meetings, memories, and entities from SQLite")
    print("- All embeddings from Qdrant")
    print("\nThis action cannot be undone!")
    
    response = input("\nAre you sure you want to continue? (yes/no): ")
    return response.lower() == 'yes'

def reset_sqlite():
    """Reset all tables in SQLite database."""
    print("\n1. Resetting SQLite database...")
    
    # Create backup first
    if os.path.exists(settings.database_path):
        backup_path = f"{settings.database_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(settings.database_path, backup_path)
        print(f"   - Created backup: {backup_path}")
    
    # Connect to new database (will create it)
    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()
    
    # Get table creation SQL from storage.py
    tables_sql = [
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            transcript TEXT NOT NULL,
            participants TEXT,
            date TIMESTAMP,
            summary TEXT,
            topics TEXT,
            key_decisions TEXT,
            action_items TEXT,
            created_at TIMESTAMP NOT NULL,
            memory_count INTEGER DEFAULT 0,
            entity_count INTEGER DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            meeting_id TEXT NOT NULL,
            content TEXT NOT NULL,
            speaker TEXT,
            timestamp TEXT,
            metadata TEXT,
            entity_mentions TEXT,
            embedding_id TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            normalized_name TEXT NOT NULL,
            attributes TEXT,
            first_seen TIMESTAMP NOT NULL,
            last_updated TIMESTAMP NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS entity_states (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            state TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            meeting_id TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities(id),
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS entity_relationships (
            id TEXT PRIMARY KEY,
            from_entity_id TEXT NOT NULL,
            to_entity_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            attributes TEXT,
            timestamp TIMESTAMP NOT NULL,
            meeting_id TEXT,
            active BOOLEAN DEFAULT 1,
            FOREIGN KEY (from_entity_id) REFERENCES entities(id),
            FOREIGN KEY (to_entity_id) REFERENCES entities(id),
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS state_transitions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            from_state TEXT,
            to_state TEXT NOT NULL,
            changed_fields TEXT NOT NULL,
            reason TEXT,
            timestamp TIMESTAMP NOT NULL,
            meeting_id TEXT,
            FOREIGN KEY (entity_id) REFERENCES entities(id),
            FOREIGN KEY (meeting_id) REFERENCES meetings(id)
        )
        """
    ]
    
    # Create indexes
    indexes_sql = [
        "CREATE INDEX idx_memories_meeting ON memories(meeting_id)",
        "CREATE INDEX idx_memories_embedding ON memories(embedding_id)",
        "CREATE INDEX idx_entities_type ON entities(type)",
        "CREATE INDEX idx_entities_normalized ON entities(normalized_name)",
        "CREATE INDEX idx_entity_states_entity ON entity_states(entity_id)",
        "CREATE INDEX idx_entity_states_timestamp ON entity_states(timestamp)",
        "CREATE INDEX idx_relationships_from ON entity_relationships(from_entity_id)",
        "CREATE INDEX idx_relationships_to ON entity_relationships(to_entity_id)",
        "CREATE INDEX idx_relationships_active ON entity_relationships(active)",
        "CREATE INDEX idx_transitions_entity ON state_transitions(entity_id)",
        "CREATE INDEX idx_transitions_timestamp ON state_transitions(timestamp)"
    ]
    
    # Create all tables
    for sql in tables_sql:
        cursor.execute(sql)
        
    # Create all indexes
    for sql in indexes_sql:
        cursor.execute(sql)
    
    conn.commit()
    conn.close()
    
    print("   ✓ SQLite database reset complete")

def reset_qdrant():
    """Reset Qdrant collections."""
    print("\n2. Resetting Qdrant collections...")
    
    try:
        client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        
        # Delete and recreate memories collection
        try:
            client.delete_collection(settings.qdrant_collection)
            print(f"   - Deleted collection: {settings.qdrant_collection}")
        except:
            print(f"   - Collection {settings.qdrant_collection} didn't exist")
            
        # Delete and recreate entity embeddings collection
        try:
            client.delete_collection(settings.qdrant_entity_collection)
            print(f"   - Deleted collection: {settings.qdrant_entity_collection}")
        except:
            print(f"   - Collection {settings.qdrant_entity_collection} didn't exist")
            
        print("   ✓ Qdrant reset complete")
        
    except Exception as e:
        print(f"   ✗ Error resetting Qdrant: {e}")
        print("   Make sure Qdrant is running!")
        return False
    
    return True

def main():
    """Main reset function."""
    # Check if running in non-interactive mode
    import sys
    if not sys.stdin.isatty():
        print("\nRunning in non-interactive mode, proceeding with reset...")
    else:
        if not confirm_reset():
            print("\nReset cancelled.")
            return
    
    # Reset SQLite
    reset_sqlite()
    
    # Reset Qdrant
    if not reset_qdrant():
        print("\n⚠ Qdrant reset failed, but SQLite was reset.")
        print("You may need to manually restart Qdrant and run this again.")
    
    print("\n" + "=" * 60)
    print("RESET COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Restart the API server to recreate collections")
    print("2. Re-ingest your meeting transcripts")
    print("\nThe improved entity resolution system will now:")
    print("- Extract full entity names (with strict=true)")
    print("- Use consistent entity resolution")
    print("- Avoid creating duplicates")

if __name__ == "__main__":
    main()