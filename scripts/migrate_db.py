"""Database migration script to add embedding columns to existing databases."""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config import settings


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cursor.fetchall()]
    return column_name in columns


def migrate_database():
    """Migrate existing database to support entity embeddings."""
    print(f"Starting database migration for: {settings.database_path}")
    
    # Connect to database
    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()
    
    try:
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Check if columns already exist
        columns_to_add = []
        
        if not check_column_exists(cursor, "entities", "name_embedding"):
            columns_to_add.append(("name_embedding", "BLOB"))
            
        if not check_column_exists(cursor, "entities", "embedding_model"):
            columns_to_add.append(("embedding_model", "VARCHAR(100)"))
            
        if not check_column_exists(cursor, "entities", "embedding_generated_at"):
            columns_to_add.append(("embedding_generated_at", "TIMESTAMP"))
        
        # Add missing columns
        if columns_to_add:
            print(f"Adding {len(columns_to_add)} new columns to entities table...")
            
            for column_name, column_type in columns_to_add:
                sql = f"ALTER TABLE entities ADD COLUMN {column_name} {column_type}"
                cursor.execute(sql)
                print(f"✓ Added column: {column_name}")
        else:
            print("✓ All embedding columns already exist")
        
        # Check and create indexes if they don't exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_entities_normalized_name'
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX idx_entities_normalized_name 
                ON entities(normalized_name)
            """)
            print("✓ Created index: idx_entities_normalized_name")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_entities_type'
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX idx_entities_type 
                ON entities(type)
            """)
            print("✓ Created index: idx_entities_type")
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_entities_last_updated'
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                CREATE INDEX idx_entities_last_updated 
                ON entities(last_updated)
            """)
            print("✓ Created index: idx_entities_last_updated")
        
        # Commit transaction
        conn.commit()
        print("\n✓ Database migration completed successfully!")
        
        # Show statistics
        cursor.execute("SELECT COUNT(*) FROM entities")
        entity_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM entities 
            WHERE name_embedding IS NOT NULL
        """)
        entities_with_embeddings = cursor.fetchone()[0]
        
        print(f"\nDatabase statistics:")
        print(f"- Total entities: {entity_count}")
        print(f"- Entities with embeddings: {entities_with_embeddings}")
        print(f"- Entities needing embeddings: {entity_count - entities_with_embeddings}")
        
        if entity_count > entities_with_embeddings:
            print("\n⚠ Run generate_embeddings.py to create embeddings for existing entities")
        
    except Exception as e:
        # Rollback on error
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


def verify_migration():
    """Verify that the migration was successful."""
    conn = sqlite3.connect(settings.database_path)
    cursor = conn.cursor()
    
    try:
        # Check columns
        required_columns = ["name_embedding", "embedding_model", "embedding_generated_at"]
        missing_columns = []
        
        for column in required_columns:
            if not check_column_exists(cursor, "entities", column):
                missing_columns.append(column)
        
        if missing_columns:
            print(f"✗ Migration verification failed. Missing columns: {', '.join(missing_columns)}")
            return False
        
        # Check indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_entities_%'
        """)
        
        indexes = [row[0] for row in cursor.fetchall()]
        required_indexes = [
            "idx_entities_normalized_name", 
            "idx_entities_type", 
            "idx_entities_last_updated"
        ]
        
        missing_indexes = [idx for idx in required_indexes if idx not in indexes]
        
        if missing_indexes:
            print(f"✗ Migration verification failed. Missing indexes: {', '.join(missing_indexes)}")
            return False
        
        print("✓ Migration verified successfully!")
        return True
        
    finally:
        conn.close()


def main():
    """Run the migration."""
    print("=" * 60)
    print("Smart-Meet Lite Database Migration")
    print("=" * 60)
    print()
    
    # Check if database exists
    if not Path(settings.database_path).exists():
        print(f"✗ Database not found at: {settings.database_path}")
        print("Please run setup.py first to create the database.")
        sys.exit(1)
    
    # Run migration
    try:
        migrate_database()
        
        # Verify migration
        print("\nVerifying migration...")
        if verify_migration():
            print("\n" + "=" * 60)
            print("✓ Migration completed successfully!")
            print("=" * 60)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\n✗ Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()