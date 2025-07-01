# Claude Tasks: Smart-Meet Lite Prioritized Implementation Plan

This document contains the prioritized task plans for fixing Smart-Meet Lite's critical issues first, then enhancing functionality, with non-essential items moved to the end.

---

## Priority Levels

### 🔴 CRITICAL - Fix Immediately (Week 1)
Core functionality that's completely broken. System is unusable without these fixes.

### 🟡 ESSENTIAL - Core Features (Week 2)  
Basic functionality that needs to work reliably before adding enhancements.

### 🟢 IMPORTANT - Enhancements (Week 3)
Advanced features that add value once the foundation works.

### ⚪ NON-ESSENTIAL - Nice to Have (Week 4+)
Security hardening, monitoring, and polish that can wait until system functions.

---

## 🔴 CRITICAL FIXES - Make It Work (Week 1)

### Hyper-Detailed Task Plan: Migrate Entity Embeddings to Qdrant

**Objective**: To refactor the Smart-Meet Lite system to store and retrieve entity name embeddings directly from Qdrant, leveraging its vector search capabilities, thereby eliminating the need to load all embeddings into memory and perform manual calculations in Python.

**Why Critical**: Current implementation loads 881+ embeddings as SQLite BLOBs and performs manual cosine similarity calculations, likely causing the 135+ second query times.

**Key Impacted Modules**:
- `src/models.py` (Entity dataclass)
- `src/storage.py` (MemoryStorage - SQLite schema, Qdrant interactions)
- `src/config.py` (Application settings)
- `src/processor.py` (EntityProcessor - embedding generation/saving)
- `src/entity_resolver.py` (EntityResolver - vector matching logic)
- `scripts/` (New migration script)

---

#### Phase 1: Data Model & Storage Adaptation

**Goal**: Prepare the Entity dataclass and MemoryStorage to handle entity embeddings in Qdrant.

##### Task 1.1: Update `src/models.py` - Modify `Entity` Dataclass
- **Objective**: Remove the name_embedding, embedding_model, and embedding_generated_at fields from the Entity dataclass. These attributes will no longer be stored directly within the Entity object itself, but rather implicitly managed by Qdrant via the entity.id.
- **Action**:
  1. Open `src/models.py`.
  2. Locate the `Entity` dataclass definition.
  3. Delete the following lines:
  ```python
  name_embedding: Optional[Any] = None  # Will be np.ndarray when loaded
  embedding_model: Optional[str] = None
  embedding_generated_at: Optional[datetime] = None
  ```
- **Verification**:
  - Run a basic Python syntax check on `src/models.py`.
  - Ensure no immediate import or attribute errors in dependent files (will be addressed in later tasks).

##### Task 1.2: Update `src/config.py` - Add Qdrant Entity Collection Setting
- **Objective**: Define a new configuration setting for the dedicated Qdrant collection that will store entity embeddings.
- **Action**:
  1. Open `src/config.py`.
  2. Locate the `Settings` class.
  3. Add the following line within the `Settings` class:
  ```python
  qdrant_entity_collection: str = "entity_embeddings"
  ```
- **Verification**:
  - Ensure `settings.qdrant_entity_collection` can be accessed from other modules (e.g., `src/storage.py`).

##### Task 1.3: Update `src/storage.py` - Adapt `MemoryStorage` for Entity Embeddings in Qdrant
- **Objective**: Rework MemoryStorage to manage entity embeddings in Qdrant, including SQLite schema changes and new Qdrant interactions.

###### Sub-Task 1.3.1: Modify SQLite `entities` table schema
- **Objective**: Remove the name_embedding, embedding_model, and embedding_generated_at columns from the entities table definition in SQLite.
- **Action**:
  1. Open `src/storage.py`.
  2. Locate the `_init_sqlite` method.
  3. Find the `CREATE TABLE IF NOT EXISTS entities` SQL statement.
  4. Remove the lines defining the embedding-related columns:
  ```sql
  name_embedding BLOB,
  embedding_model VARCHAR(100),
  embedding_generated_at TIMESTAMP
  ```
- **Verification**:
  - After running the application (which calls `_init_sqlite`), connect to `smart_meet_lite.db` using sqlite3.
  - Execute `.schema entities` and confirm the removal of the specified columns.
  - **Important**: For development, deleting `smart_meet_lite.db` before running the app will ensure a clean schema. For production, a proper database migration (e.g., using `ALTER TABLE DROP COLUMN`) would be required.

###### Sub-Task 1.3.2: Add Qdrant Collection for Entity Embeddings
- **Objective**: Ensure a dedicated Qdrant collection for entity name embeddings is created upon MemoryStorage initialization.
- **Action**:
  1. In `src/storage.py`, locate the `_init_qdrant` method.
  2. Add a new collection creation call, similar to the existing one for memories, but using `settings.qdrant_entity_collection`:
  ```python
  # Ensure entity embeddings collection exists
  entity_exists = any(c.name == settings.qdrant_entity_collection for c in collections)
  if not entity_exists:
      self.qdrant.create_collection(
          collection_name=settings.qdrant_entity_collection,
          vectors_config=VectorParams(size=384, distance=Distance.COSINE),  # Assuming 384-dim embeddings
      )
  ```
- **Verification**:
  - Run the application.
  - Use the Qdrant UI or API to confirm that a new collection named "entity_embeddings" (or whatever `qdrant_entity_collection` is set to) exists.

###### Sub-Task 1.3.3: Implement `save_entity_embedding` in `MemoryStorage`
- **Objective**: Create a method to save a single entity's name embedding to the new Qdrant entity collection.
- **Action**:
  1. In `src/storage.py`, add the following new method:
  ```python
  def save_entity_embedding(self, entity_id: str, embedding: np.ndarray):
      """Save a single entity's name embedding to Qdrant."""
      if embedding.ndim > 1:
          embedding = embedding.squeeze()  # Ensure 1D vector
      
      self.qdrant.upsert(
          collection_name=settings.qdrant_entity_collection,
          points=[
              PointStruct(
                  id=entity_id,
                  vector=embedding.tolist(),
                  payload={"entity_id": entity_id}  # Store ID in payload for consistency
              )
          ]
      )
  ```
- **Verification**: (Will be part of later integration tests, but can be temporarily tested by calling it directly).

###### Sub-Task 1.3.4: Implement `get_entity_embedding` in `MemoryStorage`
- **Objective**: Create a method to retrieve a single entity's name embedding from Qdrant.
- **Action**:
  1. In `src/storage.py`, add the following new method:
  ```python
  def get_entity_embedding(self, entity_id: str) -> Optional[np.ndarray]:
      """Retrieve a single entity's name embedding from Qdrant."""
      try:
          points = self.qdrant.retrieve(
              collection_name=settings.qdrant_entity_collection,
              ids=[entity_id],
              with_vectors=True
          )
          if points:
              return np.array(points[0].vector, dtype=np.float32)
      except Exception as e:
          # Log error, e.g., entity not found in Qdrant
          import logging
          logging.warning(f"Could not retrieve embedding for entity {entity_id} from Qdrant: {e}")
      return None
  ```
- **Verification**: (Will be part of later integration tests).

###### Sub-Task 1.3.5: Implement `search_entity_embeddings` in `MemoryStorage`
- **Objective**: Create a method to search for similar entity embeddings in Qdrant. This will be used by EntityResolver.
- **Action**:
  1. In `src/storage.py`, add the following new method:
  ```python
  def search_entity_embeddings(self, query_embedding: np.ndarray, limit: int = 5) -> List[Tuple[str, float]]:
      """Search for similar entity embeddings in Qdrant."""
      if query_embedding.ndim > 1:
          query_embedding = query_embedding.squeeze()  # Ensure 1D vector
      
      results = self.qdrant.search(
          collection_name=settings.qdrant_entity_collection,
          query_vector=query_embedding.tolist(),
          limit=limit,
          with_payload=False  # Only need ID and score
      )
      return [(result.id, result.score) for result in results]
  ```
- **Verification**: (Will be part of later integration tests).

###### Sub-Task 1.3.6: Implement `get_entity` by ID in `MemoryStorage`
- **Objective**: Provide a way to retrieve a full Entity object by its ID from SQLite, which will be needed by EntityResolver after a Qdrant search.
- **Action**:
  1. In `src/storage.py`, add the following new method:
  ```python
  def get_entity(self, entity_id: str) -> Optional[Entity]:
      """Get entity by ID."""
      conn = sqlite3.connect(self.db_path)
      conn.row_factory = sqlite3.Row
      cursor = conn.cursor()
      
      cursor.execute(
          """
          SELECT * FROM entities
          WHERE id = ?
          """,
          (entity_id,),
      )
      
      row = cursor.fetchone()
      conn.close()
      
      if row:
          return self._row_to_entity(row)
      return None
  ```
- **Verification**: (Will be part of later integration tests).

###### Sub-Task 1.3.7: Remove old embedding-related methods from `MemoryStorage`
- **Objective**: Clean up methods that interacted with SQLite for embeddings.
- **Action**:
  1. In `src/storage.py`, delete the `update_entity_embedding` method that writes to SQLite BLOB.
  2. Delete the `get_entities_needing_embeddings` method.
- **Verification**: Ensure no other parts of `storage.py` or other modules are calling these removed methods (will be handled in later tasks).

###### Sub-Task 1.3.8: Update `_row_to_entity` in `MemoryStorage`
- **Objective**: Remove the logic for deserializing name_embedding from the SQLite row, as it's no longer stored there.
- **Action**:
  1. In `src/storage.py`, locate `_row_to_entity`.
  2. Remove the code block that handles `name_embedding`, `embedding_model`, `embedding_generated_at` deserialization.

---

#### Phase 2: Ingestion & Embedding Generation Rework

**Goal**: Adjust EntityProcessor to save entity embeddings to Qdrant.

##### Task 2.1: Update `src/processor.py` - Rework Entity Embedding Generation and Saving
- **Objective**: Modify EntityProcessor to save new entity embeddings to Qdrant instead of triggering background SQLite updates.
- **Action**:
  1. Open `src/processor.py`.
  2. Locate the `_generate_embeddings_async` method.
  3. Inside the nested `generate` function, change the call from `self.storage.update_entity_embedding(entity.id, embedding)` to `self.storage.save_entity_embedding(entity.id, embedding)`.
- **Verification**:
  - During ingestion, monitor logs to confirm that `logging.info(f"Generated embedding for entity: {entity.name}")` is still triggered and that no errors related to `save_entity_embedding` occur.
  - Check the Qdrant UI/API to see new points appearing in the `entity_embeddings` collection after entity ingestion.

---

#### Phase 3: Entity Resolution & Query Rework

**Goal**: Modify EntityResolver to fetch embeddings from Qdrant for vector-based entity matching.

##### Task 3.1: Update `src/entity_resolver.py` - Adapt to Qdrant for Entity Embeddings
- **Objective**: Modify EntityResolver to use Qdrant for vector-based entity matching.

###### Sub-Task 3.1.1: Remove `_entity_embeddings` cache and `_precompute_embeddings`
- **Objective**: Remove the in-memory cache of entity embeddings since they'll be fetched from Qdrant on demand.
- **Action**:
  1. In `src/entity_resolver.py`, remove the `self._entity_embeddings: Dict[str, np.ndarray] = {}` initialization from `__init__`.
  2. Remove the entire `_precompute_embeddings` method.
  3. Remove any calls to `_precompute_embeddings` (e.g., from `_get_cached_entities`).

###### Sub-Task 3.1.2: Update `_try_vector_match` to use Qdrant
- **Objective**: Rewrite vector matching to search in Qdrant instead of in-memory calculations.
- **Action**:
  1. Replace the current `_try_vector_match` implementation with:
  ```python
  def _try_vector_match(self, term: str, context: Optional[str] = None) -> List[EntityMatch]:
      """Try to match entity using vector similarity via Qdrant."""
      logger.info(f"Attempting vector match for: {term}")
      
      # Generate embedding for the search term
      term_embedding = self.embeddings.encode(term)
      
      # Search in Qdrant
      results = self.storage.search_entity_embeddings(
          query_embedding=term_embedding,
          limit=10  # Get more candidates for better matching
      )
      
      matches = []
      for entity_id, score in results:
          if score > self.vector_threshold:  # Still use threshold
              entity = self.storage.get_entity(entity_id)
              if entity:
                  matches.append(
                      EntityMatch(
                          entity=entity,
                          confidence=float(score),
                          match_type="vector",
                          match_reason=f"Vector similarity: {score:.2f}"
                      )
                  )
      
      logger.info(f"Vector match found {len(matches)} entities above threshold")
      return matches
  ```

###### Sub-Task 3.1.3: Update entity embedding generation in `resolve_entities`
- **Objective**: When a new entity is resolved, ensure its embedding is saved to Qdrant.
- **Action**:
  1. In the `resolve_entities` method, locate where new entity embeddings are generated.
  2. Replace the threading call with direct Qdrant saving:
  ```python
  # Generate and save embedding for resolved entity
  if resolved_entity and resolved_entity.id:
      embedding = self.embeddings.encode(resolved_entity.name)
      self.storage.save_entity_embedding(resolved_entity.id, embedding)
      logger.info(f"Saved embedding for resolved entity: {resolved_entity.name}")
  ```

###### Sub-Task 3.1.4: Remove SQLite embedding references
- **Objective**: Clean up any remaining references to SQLite-stored embeddings.
- **Action**:
  1. Remove any code that accesses `entity.name_embedding`.
  2. Remove any code that checks `entity.embedding_model` or `entity.embedding_generated_at`.
  3. Update any logging or debugging code that references these removed fields.

---

#### Phase 4: Migration Script

**Goal**: Create a script to migrate existing entity embeddings from SQLite to Qdrant.

##### Task 4.1: Create Migration Script
- **Objective**: Safely migrate all 881 existing entity embeddings to Qdrant.
- **Action**:
  1. Create `scripts/migrate_entity_embeddings.py`:
  ```python
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
  ```
- **Verification**:
  - Run the script: `python scripts/migrate_entity_embeddings.py`
  - Check that backup file is created
  - Monitor migration progress in logs
  - Verify sample embeddings match

---

#### Phase 5: Testing and Rollback

**Goal**: Ensure the migration is successful and provide rollback capability.

##### Task 5.1: Integration Testing
- **Objective**: Test all entity resolution functionality with the new architecture.
- **Action**:
  1. Create `tests/test_entity_qdrant_migration.py`:
  ```python
  import pytest
  import numpy as np
  from src.storage import MemoryStorage
  from src.entity_resolver import EntityResolver
  from src.models import Entity
  
  def test_entity_embedding_storage():
      """Test saving and retrieving entity embeddings from Qdrant."""
      storage = MemoryStorage()
      
      # Create test entity
      entity = Entity(
          id="test-entity-1",
          type="project",
          name="Test Project Alpha",
          normalized_name="test project alpha"
      )
      
      # Generate and save embedding
      embedding = np.random.rand(384).astype(np.float32)
      storage.save_entity_embedding(entity.id, embedding)
      
      # Retrieve and verify
      retrieved = storage.get_entity_embedding(entity.id)
      assert retrieved is not None
      assert np.allclose(embedding, retrieved)
  
  def test_entity_similarity_search():
      """Test vector similarity search for entities."""
      storage = MemoryStorage()
      resolver = EntityResolver(storage)
      
      # Create and save test entities with embeddings
      entities = [
          ("Mobile App Redesign", "project"),
          ("Mobile Application Update", "project"),
          ("Desktop Software Revision", "project")
      ]
      
      for name, entity_type in entities:
          entity = Entity(
              id=f"test-{name.lower().replace(' ', '-')}",
              type=entity_type,
              name=name,
              normalized_name=name.lower()
          )
          storage.save_entities([entity])
          
          # Generate and save embedding
          embedding = resolver.embeddings.encode(name)
          storage.save_entity_embedding(entity.id, embedding)
      
      # Search for similar entities
      matches = resolver._try_vector_match("Mobile App Development")
      
      assert len(matches) > 0
      assert matches[0].entity.name in ["Mobile App Redesign", "Mobile Application Update"]
      assert matches[0].confidence > 0.7
  ```

##### Task 5.2: Performance Testing
- **Objective**: Ensure query performance improves with Qdrant.
- **Action**:
  1. Create a performance test script that:
     - Times entity resolution with 1000+ entities
     - Compares before/after migration times
     - Tests concurrent query handling

##### Task 5.3: Rollback Plan
- **Objective**: Provide a way to revert if issues occur.
- **Action**:
  1. Keep the backup file from migration
  2. Temporarily keep SQLite embedding columns (don't drop immediately)
  3. Add a feature flag to switch between Qdrant and SQLite:
  ```python
  # In config.py
  use_qdrant_for_entities: bool = True
  
  # In entity_resolver.py
  if settings.use_qdrant_for_entities:
      # Use Qdrant search
  else:
      # Fall back to SQLite (old code)
  ```

---

### Task 1.2: Address Query Performance Bottlenecks

**Objective**: Identify and eliminate remaining performance bottlenecks in the query flow.

**Why Critical**: Queries take 135+ seconds even after entity embedding migration.

#### Sub-Task 1.2.1: Profile the 135-second query
- **Objective**: Pinpoint exact time spent in each step of the query execution.
- **Action**:
  1. Add detailed timing logs (`time.perf_counter()`) to `src/api.py` (query endpoint), `src/query_engine.py` (all handler methods), `src/entity_resolver.py` (each resolution strategy), and `src/storage.py` (all database calls).
  2. Run the problematic 135-second query.
  3. Analyze logs to identify the slowest components.
- **Verification**: Clear identification of where the majority of query time is spent.

#### Sub-Task 1.2.2: Fix N+1 Query Patterns
- **Objective**: Optimize database access by reducing the number of individual queries.
- **Action**:
  1. `storage.py:856-872` (Search results): Modify `MemoryStorage.search` to fetch all relevant entities and meeting details in a single batch query (e.g., using `WHERE id IN (...)`) rather than individual lookups for each search result.
  2. Other areas: Review other parts of the codebase (e.g., `api.py` endpoints that fetch related data) for similar N+1 patterns and implement eager loading or batch fetching.
- **Verification**: Profiling shows a significant reduction in database query count and time for affected operations.

#### Sub-Task 1.2.3: Remove LLM Entity Limit and Truncations
- **Objective**: Ensure full data is processed and returned, removing arbitrary limits.
- **Action**:
  1. `entity_resolver.py:279`: Remove or significantly increase the `entities[:200]` limit when sending entities to the LLM for resolution. (Note: This might increase LLM token usage, requiring careful monitoring).
  2. `entity_resolver.py:290`: Remove or increase the `[:50]` truncation for entity descriptions.
  3. `extractor.py:510-511`: Remove the `[:5]` limit for decisions/action items.
  4. `query_engine.py:491`: Remove the `[:5]` limit for timeline changes.
  5. `query_engine.py:590`: Remove the `[:10]` limit for relationships processed.
- **Verification**: Confirm that all relevant data is returned in query results without arbitrary truncation.

---

### Task 1.3: Fix Threading Issues

**Objective**: Eliminate race conditions and ensure safe concurrent operations, particularly for embedding generation.

**Why Critical**: Intermittent 500 errors during rapid ingestions due to SQLite not being thread-safe.

#### Sub-Task 1.3.1: Disable background threading temporarily
- **Objective**: Immediately stop race conditions and simplify debugging.
- **Action**:
  1. `processor.py:388`: Comment out or remove the `threading.Thread(...).start()` call in `_generate_embeddings_async`. Instead, call the `generate()` function directly (synchronously).
  2. `entity_resolver.py:97-100`: Comment out or remove the `threading.Thread(...).start()` call in `_precompute_embeddings` (if not already removed by Task 1.1).
- **Verification**: No more intermittent 500 errors during rapid ingestions. Ingestion might be slower, but it will be stable.

#### Sub-Task 1.3.2: Implement a proper task queue for background operations
- **Objective**: Replace fire-and-forget threads with a robust, controlled, and scalable background processing system.
- **Action**:
  1. Choose a task queue: Research and select a suitable Python task queue (e.g., Celery with Redis/RabbitMQ, or RQ with Redis). For Smart-Meet Lite, RQ might be simpler to integrate initially.
  2. Integrate task queue:
     - Install necessary packages (e.g., `rq`, `redis`).
     - Set up a Redis server (can be another Docker container).
     - Modify `_generate_embeddings_async` in `src/processor.py` to enqueue the embedding generation task to the queue instead of running it in a new thread.
     - Create a worker script to process tasks from the queue.
     - Ensure `storage.update_entity_embedding` (now `storage.save_entity_embedding` to Qdrant) is called within the enqueued task.
- **Verification**:
  - Ingestion remains stable under high concurrency.
  - Embedding generation happens asynchronously without blocking the main API thread.
  - Monitor the task queue to ensure tasks are processed successfully.

---

### Task 1.4: Implement Connection Pooling

**Objective**: Prevent database connection exhaustion and improve performance by reusing connections.

**Why Critical**: No connection pooling leads to connection exhaustion under load.

- **Action**:
  1. For SQLite:
     - Modify `src/storage.py` to use a connection pool for SQLite. The `sqlite3` module doesn't have built-in pooling, so a simple custom pool or a library like `sqlitepool` could be used.
     - Alternatively, if moving to SQLAlchemy (as suggested in `001-Project Setup...`), SQLAlchemy's engine handles pooling automatically.
  2. For Qdrant: The `QdrantClient` typically manages its own connections, but ensure it's initialized once as a singleton or within a FastAPI dependency.
  3. For OpenAI/OpenRouter: The `httpx.Client` used by `openai.OpenAI` client should be reused across requests (e.g., initialized once in `api.py` and passed down, or as a singleton).
- **Verification**:
  - No "database locked" errors or connection exhaustion issues under load.
  - Profiling shows reduced overhead for establishing database connections.

---

### Task 1.5: Address Hardcoded Thresholds

**Objective**: Review and adjust hardcoded thresholds that might be too restrictive or arbitrary.

**Why Critical**: Score > 80 threshold is rejecting valid entity matches.

- **Action**:
  1. `processor.py:180` (Fuzzy match score): Lower the `if score > 80` threshold to a more reasonable value (e.g., 60 or 70) to allow more valid fuzzy matches.
  2. `entity_resolver.py:212` (Vector matching minimum): Review the `if best_score > 0.5` threshold. This might need adjustment based on the quality of embeddings and the desired recall/precision trade-off.
  3. Various confidence thresholds: Review and make configurable (e.g., in `src/config.py`) the confidence thresholds used in `query_engine.py` (e.g., 0.7, 0.8, 0.6, 0.3) to allow tuning.
- **Verification**: Improved entity resolution accuracy and query results, especially for less-than-perfect matches.

---

## 🟡 ESSENTIAL FIXES - Core Functionality (Week 2)

### Task 2.1: Implement Transaction Management

**Objective**: Ensure multi-table updates are atomic, preventing partial failures and data inconsistency.

- **Action**:
  1. `storage.py`: Modify methods that perform multiple INSERT/UPDATE operations across different tables (e.g., `save_entities`, `save_relationships`, `save_transitions`, and especially the ingestion flow in `api.py` that orchestrates multiple storage calls) to use SQLite transactions (`BEGIN TRANSACTION`; ... `COMMIT`; or `conn.commit()` after all operations, and `conn.rollback()` on error).
  2. API Ingestion: Ensure the entire ingestion process in `api.py` (which involves saving meeting, entities, memories, states, relationships) is treated as a single logical transaction. If any step fails, all changes should be rolled back.
- **Verification**:
  - Test scenarios where a part of the ingestion process fails (e.g., simulate a database error).
  - Confirm that either all data is saved or none is, maintaining data integrity.

---

### Task 2.2: Improve Cache Coherency

**Objective**: Address stale data issues caused by the 5-minute entity cache TTL without invalidation on updates.

- **Action**:
  1. `entity_resolver.py`: Implement a mechanism to invalidate or refresh the `_entity_cache` in EntityResolver when entities are updated or created.
     - Option A (Event-driven): If a task queue is implemented (Task 1.3.2), a message could be sent to invalidate the cache.
     - Option B (Direct invalidation): Modify `storage.save_entities` to directly call a cache invalidation method on the EntityResolver instance (if it's accessible, e.g., via dependency injection).
  2. Review other caches: Identify any other implicit caches that might suffer from stale data.
- **Verification**: Changes to entities are immediately reflected in queries that rely on the EntityResolver's cache.

---

### Task 2.3: Enhance Error Handling & Logging

**Objective**: Provide better visibility into failures, especially silent ones.

- **Action**:
  1. Comprehensive Logging: Review all try-except blocks across the codebase (especially in `api.py`, `extractor.py`, `processor.py`, `query_engine.py`, `storage.py`) and ensure:
     - Errors are logged with appropriate severity (e.g., `logger.error`, `logger.warning`).
     - Full tracebacks are included for critical errors (`traceback.format_exc()`).
     - Contextual information (e.g., `entity_id`, `meeting_id`, `query`) is included in log messages.
  2. Propagate Errors from Background Tasks: Ensure that errors occurring in background tasks (e.g., embedding generation via task queue) are logged and, if critical, reported back to a central monitoring system or a dedicated error log.
  3. Custom Exceptions: Define custom exception classes for specific application errors (e.g., `EntityNotFoundError`, `ExtractionFailedError`) to provide more granular error handling and clearer API responses.
- **Verification**: All failures are logged with sufficient detail to diagnose the root cause without needing to reproduce the issue.

---

### Task 2.4: Address Missing Functionality (`_update_meeting_entity_count`)

**Objective**: Implement the placeholder function to correctly update meeting entity counts.

- **Action**:
  1. `processor.py:326`: Implement `_update_meeting_entity_count` to update the `entity_count` column in the `meetings` table in SQLite.
     - This will involve a call to `storage.py` to update the meeting record.
  2. `storage.py`: Add a method (e.g., `update_meeting_entity_count(meeting_id: str, count: int)`) to perform the SQLite UPDATE operation.
- **Verification**: After ingestion, the `entity_count` for each meeting in the `meetings` table is accurate.

---

### Task 2.5: Robust Date Calculation Implementation

**Objective**: Accurately parse and normalize various date and time expressions from transcripts and queries.

- **Action**:
  1. Identify a suitable library: Research and integrate a robust natural language date/time parsing library (e.g., `dateparser`, `parsedatetime`).
  2. Create a dedicated module: Create `src/date_parser.py` to encapsulate date parsing logic.
  3. Implement parsing for common patterns: Handle relative dates ("next week", "last month"), specific days ("Tuesday"), quarters ("Q3"), and ambiguous phrases.
  4. Handle edge cases and ambiguity: Implement logic to resolve ambiguities (e.g., "May" could be a month or a person's name, requiring context).
  5. Add support for business days vs. calendar days: If relevant for specific BI queries (e.g., "due in 5 business days"), integrate this logic.
  6. Integrate into `extractor.py`: Use the new date parser when extracting deadline entities or action_items with due dates.
  7. Integrate into `query_engine.py`: Use the new date parser when interpreting temporal filters in user queries (e.g., `intent.time_range`).
- **Verification**: Dates extracted from transcripts and parsed from queries are consistently normalized to datetime objects, and temporal queries yield accurate results.

---

### Task 2.6: Enhanced Implicit Reference Resolution

**Objective**: Improve entity linking by resolving implicitly referred entities.

- **Action**:
  1. `entity_resolver.py`: Enhance EntityResolver to:
     - Implement pattern extraction for implicit references: Develop regex patterns or LLM prompts to identify phrases like "the project," "that feature," "our team" and link them to recently mentioned or contextually relevant entities.
     - Build candidate finding logic: When an implicit reference is found, search for candidate entities based on recent mentions, entity type, and semantic similarity to the implicit phrase.
     - Add confidence decay calculation: Introduce a mechanism to reduce the confidence of an implicit match based on temporal distance or ambiguity.
  2. Integrate into `processor.py`: Ensure EntityProcessor uses this enhanced resolution during ingestion.
- **Verification**: Fewer "unresolved" entities, and the knowledge graph becomes more complete by linking implicit mentions.

---

### Task 2.7: Technical Content Extraction

**Objective**: Structure technical data (data models, specs) directly from meeting discussions.

- **Action**:
  1. Create `src/technical_extractor.py`: Implement the `TechnicalContentExtractor` class as provided in the example, with methods like `extract_data_model` and `extract_technical_specification`.
  2. Integrate into `src/extractor.py`: After the main LLM extraction, pass relevant memory chunks (e.g., those tagged as "technical discussion" or containing keywords like "schema", "API", "model") to the TechnicalContentExtractor.
  3. Store structured data: Modify the Memory or Entity models (or create new ones) to store this structured technical content (e.g., as a JSON field in `Memory.metadata` or `Entity.attributes`).
- **Verification**: Technical content (e.g., a data model definition) is extracted from transcripts and stored in a structured, queryable format.

---

### Task 2.8: EML File Processing

**Objective**: Implement proper email parsing for .eml files, extracting meeting content, participants, and attachments.

- **Action**:
  1. Identify a suitable library: Use Python's built-in `email` module or a more specialized library.
  2. Create a dedicated module: Create `src/eml_parser.py`.
  3. Implement parsing logic:
     - Extract Subject as meeting title.
     - Extract From, To, Cc as participants.
     - Extract the main body content (handling plain text and HTML).
     - Identify and extract attachments (if relevant for meeting context).
  4. Integrate into `api.py` (`ingest_file` endpoint): When an .eml file is uploaded, use the eml_parser to extract the transcript and metadata before passing it to the main ingestion pipeline.
  5. Update `ingest_eml_files.py`: Modify the existing script to use the new eml_parser.
- **Verification**: .eml files are ingested correctly, with accurate titles, participants, and transcript content.

---

## 🟢 IMPORTANT - Advanced Features (Week 3)

### Task 3.1: Comprehensive Query Processing Pipeline

**Objective**: Orchestrate dual retrieval and LLM summarization to provide a comprehensive "current state" narrative.

- **Action**:
  1. `src/query_engine.py` - Rework `answer_query`:
     - LLM Query Orchestrator: Introduce a new orchestrator function (or significantly refactor `answer_query`) that uses an LLM to understand the user's query, temporal intent, and plan the retrieval strategy. This LLM will guide the subsequent steps.
     - Dual Retrieval:
       - Semantic Search: Continue using `storage.search` (Qdrant for memories).
       - Keyword Search: Implement `storage.keyword_search_memories` (SQLite LIKE queries on `memories.content`).
       - Temporal/Structured Retrieval: Implement `storage.get_temporal_data` (or similar) to retrieve relevant EntityState changes, StateTransition records, and EntityRelationship changes, potentially filtered by time or entity.
       - Parallel Execution: Execute these retrieval methods in parallel (e.g., using `asyncio` if the FastAPI app is async, or `concurrent.futures.ThreadPoolExecutor`).
     - Context Assembly: Collect all relevant chunks (memories, entity states, relationships, technical content) from the dual retrieval. Order them chronologically.
     - LLM Summarization: Feed the assembled, chronologically ordered context into a powerful LLM (e.g., `anthropic/claude-3-haiku` or a more capable model if needed) with a prompt to:
       - Summarize the "current state" of the subject.
       - Highlight key changes and evolution over time.
       - Identify any unresolved issues or open questions.
       - Provide a concise, narrative answer.
  2. `src/storage.py` - Add Keyword Search: Implement `keyword_search_memories(query: str, limit: int = 10) -> List[Memory]` using SQLite LIKE queries on `memories.content`.
  3. `src/storage.py` - Add Temporal Data Retrieval: Implement methods like `get_entity_state_history(entity_id, time_range)` and `get_relationships_over_time(entity_id, time_range)` to support the temporal retrieval.
- **Verification**:
  - Queries like "What's the current version of the test framework data model?" return a narrative summary of its evolution and current state, not just raw memories.
  - Performance remains acceptable due to parallel retrieval.

---

### Task 3.2: Enhanced Temporal Awareness and Extraction

**Objective**: Integrate TemporalMemoryChunk and TemporalExtractor concepts for richer temporal data.

- **Action**:
  1. `src/models.py`: Define the `TemporalMemoryChunk` dataclass as provided in the example, including fields like `temporal_markers`, `version_info`, `references_past`, `creates_future`, `structured_data`, etc.
  2. `src/extractor.py`: Refactor `MemoryExtractor` into a `TemporalExtractor` (or create a new one) that implements the `extract_temporal_chunks` method.
     - Implement `_segment_transcript` for intelligent transcript segmentation.
     - Implement `_extract_section_chunks` to call the LLM with the sophisticated `extraction_prompt` to get TemporalMemoryChunk data.
     - Implement `_enhance_temporal_links` to add explicit temporal links.
     - Implement `_identify_version_chains` to link versions.
  3. Storage for Temporal Chunks: Decide how to store TemporalMemoryChunk data.
     - Option A (Enrich `memories` table): Add new columns to the `memories` table in SQLite to store the additional temporal metadata (e.g., `temporal_markers` as JSON, `version_info` as JSON).
     - Option B (New table): Create a new `temporal_chunks` table in SQLite.
     - Option C (Graph DB): If a graph database (e.g., Neo4j) is introduced later, this data would naturally fit there. For now, SQLite is the target.
  4. Update Ingestion Pipeline: Ensure `api.py`'s ingestion process uses the TemporalExtractor and saves the richer TemporalMemoryChunk data.
- **Verification**: Ingested data now contains detailed temporal markers, version information, and explicit links to past/future events.

---

### Task 3.3: Enhanced Query Intent Understanding with LLM

**Objective**: Refine the LLM's ability to classify intent and extract entities with high precision.

- **Action**:
  1. `src/query_engine.py` - Refine `parse_intent` prompt: Update the system prompt for `parse_intent` to:
     - Emphasize capturing all relevant entities, including implicit ones.
     - Guide the LLM to identify temporal aspects (e.g., "current," "historical," "future").
     - Encourage more nuanced intent classification (e.g., distinguishing between "status" and "progress update").
  2. Evaluate LLM Model: Consider if `anthropic/claude-3-haiku` is sufficient for complex intent parsing, or if a more capable model (e.g., `claude-3-opus`, `gpt-4-turbo`) is needed for this specific task.
- **Verification**: Intent parsing is highly accurate, even for complex and ambiguous queries.

---

## ⚪ NON-ESSENTIAL - Nice to Have (Week 4+)

### Task 4.1: Security Hardening

**Objective**: Address critical security vulnerabilities.

**Why Non-Essential**: System must work before we secure it. These are production concerns, not functionality fixes.

- **Action**:
  1. CORS Restriction: `api.py`: Change `allow_origins=["*"]` to a specific list of allowed origins (e.g., `["http://localhost:3000", "https://your-frontend.com"]`).
  2. SSL Verification: `query_engine.py` and `extractor.py`: Remove `verify=False` from `httpx.Client` and `warnings.filterwarnings("ignore", message="Unverified HTTPS request")`. Instead, ensure proper SSL certificate configuration in the environment.
  3. API Key Management: Ensure `settings.openrouter_api_key` is loaded securely (e.g., only from environment variables, not committed to source control).
- **Verification**:
  - CORS policies are correctly enforced.
  - SSL connections are verified.
  - API keys are not exposed.

---

### Task 4.2: Configuration Centralization

**Objective**: Ensure all configurable parameters are loaded from `src/config.py`.

**Why Non-Essential**: Hardcoded values work for development. This is a maintainability improvement.

- **Action**:
  1. `smart_meet_client.py`: Change `base_url: str = "http://localhost:8000"` to load from `settings.api_host` and `settings.api_port`.
  2. Review all modules: Conduct a thorough review of all modules to ensure no other hardcoded values exist that should be configurable.
- **Verification**: All configuration is managed centrally through `src/config.py`.

---

### Task 4.3: Testing Strategy Enhancement

**Objective**: Implement comprehensive unit and integration tests.

**Why Non-Essential**: Testing is important but doesn't fix the broken system. Focus on making it work first.

- **Action**:
  1. Unit Test Coverage: Increase unit test coverage for all modules, especially `src/processor.py`, `src/entity_resolver.py`, `src/query_engine.py`, and `src/storage.py`.
  2. Integration Tests: Expand `test_system.py` and other integration tests to cover end-to-end flows, including ingestion, complex queries, and new advanced features.
  3. Mock External Dependencies: Use mocking frameworks (e.g., `unittest.mock`) to mock LLM API calls, Qdrant interactions, and external file system access in unit tests.
  4. Performance Tests: Develop dedicated performance tests to continuously monitor query response times, ingestion rates, and resource utilization.
- **Verification**: High test coverage, reliable test suite, and automated performance monitoring.

---

### Task 4.4: LLM Prompt Management

**Objective**: Externalize LLM prompts and schemas for easier iteration.

**Why Non-Essential**: Inline prompts work fine. This is an optimization for future flexibility.

[Implementation details follow as in original document...]

---

### Task 4.5: Data Lifecycle Management

**Objective**: Implement strategies for managing data growth and ensuring long-term data health.

**Why Non-Essential**: Data growth is a future problem. Fix current functionality first.

[Implementation details follow as in original document...]

---

### Task 4.6: Monitoring & Optimization

**Objective**: Implement metrics and continuous optimization.

**Why Non-Essential**: Can't monitor what doesn't work. Fix functionality before adding observability.

[Implementation details follow as in original document...]

---

### Task 4.7: API Design Gaps

**Objective**: Implement missing API endpoints.

**Why Non-Essential**: Core queries must work before adding convenience endpoints.

[Implementation details follow as in original document...]

---

### Task 3.4: Expertise Modeling

**Objective**: Identify and track areas of expertise for individuals based on meeting discussions.

**Why Non-Essential**: Advanced analytics feature that requires working basic queries first.

[Implementation details follow as in original document...]

---

### Task 3.5: Predictive Context Assembly

**Objective**: Proactively provide relevant information and anticipate user needs.

**Why Non-Essential**: Can't predict the future when we can't query the present. Most advanced feature.

[Implementation details follow as in original document...]

---

## Implementation Timeline Summary

### Week 1: Emergency Fixes & Core Functionality
- **Day 1-2**: Entity embedding migration to Qdrant
- **Day 3**: Query profiling, remove hardcoded limits
- **Day 4**: Fix threading issues, implement connection pooling
- **Day 5**: Lower thresholds, verify <5 second queries

### Week 2: Essential Features
- **Day 1-2**: Transaction management, cache coherency
- **Day 3**: Error handling, missing functionality
- **Day 4**: Date parsing, implicit reference resolution
- **Day 5**: Technical extraction, EML parsing

### Week 3: Advanced Intelligence
- **Day 1-2**: Comprehensive query pipeline
- **Day 3-4**: Temporal awareness, enhanced intent parsing
- **Day 5**: Integration testing

### Week 4+: Non-Essential Improvements
- Security hardening
- Configuration management
- Testing suite
- Monitoring
- Advanced analytics

---

## Success Metrics

### Week 1 Target (Critical)
- Query response time: <5 seconds (from 135+ seconds)
- Entity resolution accuracy: >80% (from 0%)
- No threading errors
- Stable under 5 concurrent users

### Week 2 Target (Essential)
- Query response time: <3 seconds
- Entity resolution accuracy: >90%
- All data consistently saved
- Proper error visibility

### Week 3 Target (Important)
- Query response time: <2 seconds
- Rich temporal understanding
- Narrative answers, not just data
- Advanced query types working

### Final Target (With Non-Essentials)
- Production-ready security
- Comprehensive monitoring
- 80%+ test coverage
- Predictive intelligence

---

This prioritized plan ensures we fix the broken foundation before adding features or hardening for production.