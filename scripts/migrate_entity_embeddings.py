#!/usr/bin/env python3
"""
Migrate entity embeddings from SQLite BLOBs to Qdrant vector database.

This script:
1. Backs up existing embeddings to JSON
2. Reads embeddings from SQLite
3. Saves them to Qdrant
4. Verifies the migration
"""

import json
import sqlite3
import numpy as np
from datetime import datetime
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.storage import MemoryStorage
from src.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_embeddings(db_path: str, backup_file: str = "entity_embeddings_backup.json"):
    """Backup all entity embeddings to JSON file."""
    logger.info(f"Backing up embeddings to {backup_file}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, name_embedding, embedding_model, embedding_generated_at
        FROM entities
        WHERE name_embedding IS NOT NULL
    """)
    
    embeddings = {}
    count = 0
    
    for row in cursor.fetchall():
        try:
            # Deserialize embedding
            embedding_bytes = row['name_embedding']
            embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
            
            embeddings[row['id']] = {
                'name': row['name'],
                'embedding': embedding.tolist(),
                'model': row['embedding_model'],
                'generated_at': row['embedding_generated_at']
            }
            count += 1
        except Exception as e:
            logger.error(f"Failed to backup embedding for entity {row['id']}: {e}")
    
    conn.close()
    
    with open(backup_file, 'w') as f:
        json.dump({
            'backup_date': datetime.now().isoformat(),
            'total_embeddings': count,
            'embeddings': embeddings
        }, f, indent=2)
    
    logger.info(f"Backed up {count} embeddings")
    return embeddings


def migrate_embeddings(storage: MemoryStorage, embeddings: dict):
    """Migrate embeddings to Qdrant."""
    logger.info(f"Starting migration of {len(embeddings)} embeddings to Qdrant")
    
    success_count = 0
    failed_ids = []
    
    for entity_id, data in embeddings.items():
        try:
            # Convert list back to numpy array
            embedding = np.array(data['embedding'], dtype=np.float32)
            
            # Save to Qdrant
            storage.save_entity_embedding(entity_id, embedding)
            
            # Verify it was saved
            retrieved = storage.get_entity_embedding(entity_id)
            if retrieved is not None:
                success_count += 1
                if success_count % 100 == 0:
                    logger.info(f"Migrated {success_count} embeddings...")
            else:
                logger.error(f"Failed to verify embedding for {entity_id}")
                failed_ids.append(entity_id)
                
        except Exception as e:
            logger.error(f"Failed to migrate {entity_id}: {e}")
            failed_ids.append(entity_id)
    
    logger.info(f"Migration complete: {success_count}/{len(embeddings)} successful")
    if failed_ids:
        logger.error(f"Failed entity IDs: {failed_ids}")
    
    return success_count, failed_ids


def verify_migration(storage: MemoryStorage, original_embeddings: dict, sample_size: int = 10):
    """Verify that migrated embeddings match originals."""
    logger.info(f"Verifying migration with {sample_size} random samples")
    
    import random
    sample_ids = random.sample(list(original_embeddings.keys()), 
                              min(sample_size, len(original_embeddings)))
    
    mismatches = []
    for entity_id in sample_ids:
        original = np.array(original_embeddings[entity_id]['embedding'])
        retrieved = storage.get_entity_embedding(entity_id)
        
        if retrieved is None:
            mismatches.append((entity_id, "Not found in Qdrant"))
        elif not np.allclose(original, retrieved, rtol=1e-5):
            mismatches.append((entity_id, "Embedding values don't match"))
    
    if mismatches:
        logger.error(f"Verification failed for {len(mismatches)} samples: {mismatches}")
    else:
        logger.info("Verification successful - all samples match!")
    
    return len(mismatches) == 0


def main():
    """Main migration process."""
    logger.info("Starting entity embeddings migration to Qdrant")
    
    # Initialize storage
    storage = MemoryStorage()
    
    # Step 1: Backup
    embeddings = backup_embeddings(settings.database_path)
    
    if not embeddings:
        logger.warning("No embeddings found to migrate")
        return
    
    # Step 2: Migrate
    success_count, failed_ids = migrate_embeddings(storage, embeddings)
    
    # Step 3: Verify
    if success_count > 0:
        verify_migration(storage, embeddings)
    
    # Step 4: Report
    logger.info(f"""
Migration Summary:
- Total embeddings: {len(embeddings)}
- Successfully migrated: {success_count}
- Failed: {len(failed_ids)}
- Backup saved to: entity_embeddings_backup.json

Next steps:
1. If migration was successful, update the code to remove SQLite embedding columns
2. Test the application thoroughly
3. Keep the backup file until you're confident everything works
""")


if __name__ == "__main__":
    main()