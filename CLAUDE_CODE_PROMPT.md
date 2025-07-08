# Claude Code Prompt for Smart-Meet Lite Query Engine Fix

Copy and paste this prompt into a new Claude Code conversation to continue fixing the Smart-Meet Lite system:

---

## Prompt:

I need help continuing work on the Smart-Meet Lite system. The system's core functionality has been restored - it now correctly tracks entities across meetings and monitors state changes. However, several optimization phases remain.

**CURRENT STATUS (as of 2025-01-08 04:40)**:

**Completed (2/10 planned phases):**
- ✅ **Phase 1**: String formatting fixed - no more crashes with % characters
- ✅ **Phase 2**: State normalization - all states normalize to canonical form
- ✅ **Phase 2b**: Relationship normalization (sub-phase of Phase 2)

**Critical Fix (unplanned but resolved):**
- ✅ **Entity Resolution**: Fixed missing embeddings, now tracks entities correctly

**Pending (8 phases for optimization):**
- ⏳ **Phase 3-10**: Quality and performance improvements needed

**CRITICAL FIXES JUST IMPLEMENTED**:

1. **Entity Embeddings Generation (processor_v2.py lines 760-779)**:
   - Entity embeddings were NOT being generated when entities were saved
   - Added code to generate and store embeddings in Qdrant after save_entities()
   - This enables vector similarity search to actually find entities

2. **API Entity Counting Fix (api.py lines 187-270)**:
   - Fixed incorrect logging that showed "vector: 0 + resolved: 0"
   - Now properly tracks vector_entities vs text_entities
   - Correctly passes all relevant entities to the extractor

3. **Progress and Blockers Tracking (extractor_enhanced.py lines 145-155)**:
   - Added missing "progress" and "blockers" fields to extraction schema
   - Updated extraction prompt with clear examples
   - System can now track progress percentages and blockers

4. **Cross-Type Entity Matching (processor_v2.py)**:
   - Enabled matching entities across different types (FEATURE vs PROJECT)
   - This allows "API Migration feature" to match with "API Migration project"

**TEST RESULTS CONFIRMED**:
- ✅ Entity embeddings being generated (verified in logs: "Saved embedding for entity 'API Migration'")
- ✅ Vector similarity working (API Migration found with score 0.507)
- ✅ State changes tracked properly (Project Alpha: 30% → 50%)
- ✅ Progress and blockers extracted correctly
- ✅ All queries return HTTP 200 with proper responses
- ✅ EntityType import fixed in query_engine_v2.py

**IMMEDIATE NEXT STEPS**:
1. **Start with Phase 3: Entity Extraction Improvements**
   - Common words like "What", "December", "Status" are being extracted as entities
   - Need to implement comprehensive stop word filtering
   - Update _extract_query_entities method in query_engine_v2.py
   
2. **Then Phase 4: Response Conciseness**
   - Responses are too verbose (200+ words)
   - Need to update all 7 prompt generation methods
   - Target: responses under 100 words
   
3. **Then Phase 5: Query Caching**
   - Every identical query costs money
   - Implement 5-minute in-memory cache
   - Expected 60%+ cost reduction

**KNOWN ISSUES TO ADDRESS**:
- Phase 3: Stop extracting common words as entities ("What", "December", etc.)
- Phase 4: Make responses more concise (under 100 words)
- Phase 5: Implement query caching for performance
- Phase 6-8: Various optimizations and cleanup

**ROOT CAUSE SUMMARY (RESOLVED)**:
The system wasn't tracking state changes because:
1. Entity embeddings weren't being generated → vector search returned 0 results
2. Without vector matches, the entity resolver couldn't match similar names
3. This caused duplicate entities instead of updates to existing ones
4. Missing schema fields prevented progress/blocker tracking

All these issues have been fixed and verified through testing. The system now correctly:
- Generates and stores entity embeddings in Qdrant
- Uses vector similarity to find related entities
- Tracks state changes between meetings
- Monitors progress percentages and blockers

---

## Additional Technical Details:

**Entity Resolver Configuration** (`src/entity_resolver.py`):
- Vector threshold: 0.70 (lowered from 0.85)
- Fuzzy threshold: 0.65 (lowered from 0.75)
- Already strips suffixes: 'feature', 'project', 'system', 'module', 'component', 'service', 'app', 'application'
- Uses `search_entity_embeddings` for vector similarity internally

**What Still Needs to Be Done** (from `018_Current_Plan.md`):
- **Phase 3**: Entity extraction improvements - stop extracting "What", "December", "Status" as entities
- **Phase 4**: Response conciseness - reduce from 200+ words to under 100 words
- **Phase 5**: Query caching - implement 5-minute cache for 60%+ cost reduction
- **Phase 6**: Async/await corrections - fix synchronous code in async context
- **Phase 7**: Database index fixes - correct index names
- **Phase 8**: LLM processor cleanup - remove duplicate initialization
- **Phase 9**: Comprehensive testing - full integration test suite
- **Phase 10**: Production deployment checklist

**Files to Reference**:
- `018_Current_Plan.md` - Complete roadmap with all phases
- `api_debug.log` - Check for entity resolution logs
- `test_via_api.py` - The test script to verify entity resolution
- `src/api.py` - Lines 187-250 contain the hybrid entity resolution implementation