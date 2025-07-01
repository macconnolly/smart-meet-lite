"""Generate embeddings for existing entities that don't have them."""

import sys
import time
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.storage import MemoryStorage
from src.embeddings import EmbeddingEngine
from src.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def generate_embeddings(batch_size: int = 10, show_progress: bool = True):
    """Generate embeddings for entities that need them."""
    storage = MemoryStorage()
    embeddings = EmbeddingEngine()
    
    # Track statistics
    total_processed = 0
    total_errors = 0
    start_time = time.time()
    
    while True:
        # Get batch of entities needing embeddings
        entities = storage.get_entities_needing_embeddings(limit=batch_size)
        
        if not entities:
            break
            
        logging.info(f"Processing batch of {len(entities)} entities...")
        
        for i, entity in enumerate(entities):
            try:
                # Generate embedding
                embedding = embeddings.encode(entity.name)
                if embedding.ndim > 1:
                    embedding = embedding[0]
                
                # Update in database
                storage.update_entity_embedding(entity.id, embedding)
                
                total_processed += 1
                
                if show_progress and (i + 1) % 5 == 0:
                    print(f"Progress: {i + 1}/{len(entities)} in current batch")
                    
            except Exception as e:
                logging.error(f"Failed to generate embedding for '{entity.name}': {e}")
                total_errors += 1
                continue
        
        # Brief pause between batches
        time.sleep(0.1)
    
    # Calculate statistics
    elapsed_time = time.time() - start_time
    
    return {
        'total_processed': total_processed,
        'total_errors': total_errors,
        'elapsed_time': elapsed_time,
        'embeddings_per_second': total_processed / elapsed_time if elapsed_time > 0 else 0
    }


def verify_embeddings():
    """Verify that embeddings were generated correctly."""
    storage = MemoryStorage()
    
    # Get statistics
    conn = storage.db_path
    import sqlite3
    db = sqlite3.connect(conn)
    cursor = db.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM entities")
    total_entities = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM entities WHERE name_embedding IS NOT NULL")
    entities_with_embeddings = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT embedding_model) 
        FROM entities 
        WHERE embedding_model IS NOT NULL
    """)
    unique_models = cursor.fetchone()[0]
    
    db.close()
    
    return {
        'total_entities': total_entities,
        'entities_with_embeddings': entities_with_embeddings,
        'entities_without_embeddings': total_entities - entities_with_embeddings,
        'coverage_percentage': (entities_with_embeddings / total_entities * 100) if total_entities > 0 else 0,
        'unique_models': unique_models
    }


def main():
    """Run embedding generation."""
    print("=" * 60)
    print("Smart-Meet Lite Embedding Generation")
    print("=" * 60)
    print()
    
    # Check current status
    print("Checking current embedding status...")
    before_stats = verify_embeddings()
    
    print(f"\nCurrent Status:")
    print(f"- Total entities: {before_stats['total_entities']}")
    print(f"- Entities with embeddings: {before_stats['entities_with_embeddings']}")
    print(f"- Entities without embeddings: {before_stats['entities_without_embeddings']}")
    print(f"- Coverage: {before_stats['coverage_percentage']:.1f}%")
    
    if before_stats['entities_without_embeddings'] == 0:
        print("\n✓ All entities already have embeddings!")
        return
    
    # Generate embeddings
    print(f"\nGenerating embeddings for {before_stats['entities_without_embeddings']} entities...")
    print("This may take a few minutes...\n")
    
    try:
        results = generate_embeddings(batch_size=20)
        
        print(f"\n✓ Embedding generation completed!")
        print(f"- Processed: {results['total_processed']} entities")
        print(f"- Errors: {results['total_errors']}")
        print(f"- Time: {results['elapsed_time']:.2f} seconds")
        print(f"- Speed: {results['embeddings_per_second']:.2f} embeddings/second")
        
        # Verify results
        print("\nVerifying results...")
        after_stats = verify_embeddings()
        
        print(f"\nFinal Status:")
        print(f"- Total entities: {after_stats['total_entities']}")
        print(f"- Entities with embeddings: {after_stats['entities_with_embeddings']}")
        print(f"- Coverage: {after_stats['coverage_percentage']:.1f}%")
        
        if after_stats['entities_without_embeddings'] > 0:
            print(f"\n⚠ {after_stats['entities_without_embeddings']} entities still need embeddings")
            print("This may be due to errors. Check the logs for details.")
        else:
            print("\n✓ All entities now have embeddings!")
            
    except Exception as e:
        print(f"\n✗ Embedding generation failed: {e}")
        logging.exception("Embedding generation error")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✓ Embedding generation complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()