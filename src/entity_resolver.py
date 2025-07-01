"""Advanced entity resolution system with multiple strategies."""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
from openai import OpenAI

from .models import Entity, EntityMatch, EntityType
from .storage import MemoryStorage
from .embeddings import EmbeddingEngine
from .config import settings

# Configure logging
logger = logging.getLogger(__name__)


class EntityResolver:
    """Centralized entity resolution with multiple strategies."""
    
    def __init__(self, 
                 storage: MemoryStorage, 
                 embeddings: EmbeddingEngine,
                 llm_client: OpenAI,
                 cache_ttl: int = 300,  # 5 minutes
                 vector_threshold: float = 0.85,
                 fuzzy_threshold: float = 0.75):
        self.storage = storage
        self.embeddings = embeddings
        self.llm_client = llm_client
        self.cache_ttl = timedelta(seconds=cache_ttl)
        self.vector_threshold = vector_threshold
        self.fuzzy_threshold = fuzzy_threshold
        
        # Thread-safe caching
        self._cache_lock = threading.RLock()
        self._entity_cache: Optional[List[Entity]] = None
        self._cache_time: Optional[datetime] = None
        
        # Performance metrics
        self._resolution_stats = {
            'exact_matches': 0,
            'vector_matches': 0,
            'fuzzy_matches': 0,
            'llm_matches': 0,
            'no_matches': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def _get_cached_entities(self) -> List[Entity]:
        """Get entities with thread-safe caching."""
        with self._cache_lock:
            now = datetime.now()
            
            if (self._entity_cache is None or 
                self._cache_time is None or 
                now - self._cache_time > self.cache_ttl):
                
                logger.info("Refreshing entity cache...")
                self._entity_cache = self.storage.get_all_entities()
                self._cache_time = now
                
                self._resolution_stats['cache_misses'] += 1
                logger.info(f"Entity cache refreshed with {len(self._entity_cache)} entities")
            else:
                self._resolution_stats['cache_hits'] += 1
            
            return self._entity_cache
    
    
    def resolve_entities(self, 
                        query_terms: List[str], 
                        context: Optional[str] = None) -> Dict[str, EntityMatch]:
        """
        Resolve query terms to database entities using multiple strategies.
        
        Args:
            query_terms: List of entity names/terms to resolve
            context: Optional context to help with resolution
            
        Returns:
            Dictionary mapping query terms to EntityMatch objects
        """
        if not query_terms:
            return {}
        
        entities = self._get_cached_entities()
        if not entities:
            return {term: EntityMatch(term, None, 0.0, 'no_entities') 
                    for term in query_terms}
        
        results = {}
        
        # Group terms by resolution strategy
        exact_matches = {}
        vector_candidates = {}
        fuzzy_candidates = {}
        llm_candidates = []
        
        for term in query_terms:
            # Try exact match first (fastest)
            match = self._try_exact_match(term, entities)
            if match:
                exact_matches[term] = match
                self._resolution_stats['exact_matches'] += 1
                continue
            
            # Try vector similarity
            vector_match = self._try_vector_match(term, entities)
            if vector_match and vector_match.confidence >= self.vector_threshold:
                vector_candidates[term] = vector_match
                self._resolution_stats['vector_matches'] += 1
                continue
            
            # Try fuzzy matching
            fuzzy_match = self._try_fuzzy_match(term, entities)
            if fuzzy_match and fuzzy_match.confidence >= self.fuzzy_threshold:
                fuzzy_candidates[term] = fuzzy_match
                self._resolution_stats['fuzzy_matches'] += 1
                continue
            
            # Queue for LLM resolution
            llm_candidates.append(term)
        
        # Batch LLM resolution for remaining terms
        if llm_candidates:
            llm_matches = self._resolve_with_llm(llm_candidates, entities, context)
            for term, match in llm_matches.items():
                if match.entity:
                    self._resolution_stats['llm_matches'] += 1
                else:
                    self._resolution_stats['no_matches'] += 1
            results.update(llm_matches)
        
        # Combine all results
        results.update(exact_matches)
        results.update(vector_candidates)
        results.update(fuzzy_candidates)
        
        return results
    
    def _try_exact_match(self, term: str, entities: List[Entity]) -> Optional[EntityMatch]:
        """Try exact name matching."""
        normalized_term = term.lower().strip()
        
        for entity in entities:
            if entity.normalized_name == normalized_term:
                return EntityMatch(
                    query_term=term,
                    entity=entity,
                    confidence=1.0,
                    match_type='exact'
                )
        
        return None
    
    def _try_vector_match(self, term: str, entities: List[Entity]) -> Optional[EntityMatch]:
        """Try vector similarity matching using Qdrant."""
        try:
            query_embedding = self.embeddings.encode(term)
            if query_embedding.ndim > 1:
                query_embedding = query_embedding[0]
            
            # Search Qdrant for similar entity embeddings
            qdrant_results = self.storage.search_entity_embeddings(query_embedding, limit=1)
            
            if qdrant_results:
                entity_id, score = qdrant_results[0]
                if score > 0.5:  # Minimum threshold for Qdrant match
                    # Retrieve the full entity object from SQLite
                    entity = self.storage.get_entity(entity_id)
                    if entity:
                        return EntityMatch(
                            query_term=term,
                            entity=entity,
                            confidence=score,
                            match_type='vector',
                            metadata={'similarity_score': score}
                        )
        except Exception as e:
            logger.warning(f"Vector matching failed for '{term}': {e}")
        
        return None
    
    def _try_fuzzy_match(self, term: str, entities: List[Entity]) -> Optional[EntityMatch]:
        """Try fuzzy string matching."""
        try:
            from fuzzywuzzy import fuzz
        except ImportError:
            logger.warning("fuzzywuzzy not installed, skipping fuzzy matching")
            return None
        
        term_lower = term.lower()
        best_match = None
        best_score = 0.0
        
        for entity in entities:
            entity_lower = entity.name.lower()
            
            # Multiple fuzzy strategies
            scores = [
                fuzz.ratio(term_lower, entity_lower) / 100.0,
                fuzz.partial_ratio(term_lower, entity_lower) / 100.0,
                fuzz.token_sort_ratio(term_lower, entity_lower) / 100.0,
                fuzz.token_set_ratio(term_lower, entity_lower) / 100.0
            ]
            
            # Use the best score
            max_score = max(scores)
            
            # Boost score if one contains the other
            if term_lower in entity_lower or entity_lower in term_lower:
                max_score = min(max_score * 1.2, 1.0)
            
            if max_score > best_score:
                best_score = max_score
                best_match = entity
        
        if best_match and best_score > 0.5:
            return EntityMatch(
                query_term=term,
                entity=best_match,
                confidence=best_score,
                match_type='fuzzy',
                metadata={'fuzzy_score': best_score}
            )
        
        return None
    
    def _resolve_with_llm(self, 
                         terms: List[str], 
                         entities: List[Entity],
                         context: Optional[str] = None) -> Dict[str, EntityMatch]:
        """Use LLM for complex entity resolution."""
        
        # Prepare entity catalog (limit to prevent token overflow)
        entity_catalog = []
        for entity in entities[:200]:  # Adaptive limit
            catalog_entry = {
                'id': entity.id,
                'name': entity.name,
                'type': entity.type.value,
                'keywords': []
            }
            
            # Extract keywords from attributes
            if hasattr(entity, 'attributes') and entity.attributes:
                if 'description' in entity.attributes:
                    catalog_entry['keywords'].append(entity.attributes['description'][:50])
                if 'aliases' in entity.attributes:
                    catalog_entry['keywords'].extend(entity.attributes['aliases'])
            
            entity_catalog.append(catalog_entry)
        
        # Sophisticated prompt
        system_prompt = """You are an advanced entity resolution system. Your task is to intelligently match query terms to database entities based on semantic meaning, context, and domain knowledge.

Key principles:
1. Consider semantic similarity, not just string matching
2. Understand abbreviations, synonyms, and variations
3. Use context clues when available
4. Be confident in obvious matches, conservative in ambiguous cases
5. Return null for terms that have no reasonable match

Examples of good matches:
- "mobile app redesign" → "Mobile App Redesign Project"
- "API work" → "API Optimization Initiative"
- "ML pipeline" → "Machine Learning Data Pipeline"
- "backend perf" → "Backend Performance Optimization"
"""

        user_prompt = f"""Match these query terms to the most appropriate entities.

Query terms: {json.dumps(terms)}
{f'Context: {context}' if context else ''}

Available entities:
{json.dumps(entity_catalog, indent=2)}

Return a JSON object mapping each query term to either:
- An entity ID (if confident match exists)
- null (if no reasonable match)

Include confidence scores (0-1) for each match."""

        try:
            response = self._call_llm_with_retry(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Convert to EntityMatch objects
            matches = {}
            entity_lookup = {e.id: e for e in entities}
            
            for term in terms:
                if term in result:
                    match_data = result[term]
                    if isinstance(match_data, dict) and 'entity_id' in match_data:
                        entity = entity_lookup.get(match_data['entity_id'])
                        confidence = match_data.get('confidence', 0.7)
                    elif isinstance(match_data, str):
                        entity = entity_lookup.get(match_data)
                        confidence = 0.7
                    else:
                        entity = None
                        confidence = 0.0
                    
                    matches[term] = EntityMatch(
                        query_term=term,
                        entity=entity,
                        confidence=confidence,
                        match_type='llm',
                        metadata={'llm_response': match_data}
                    )
                else:
                    matches[term] = EntityMatch(term, None, 0.0, 'llm_no_match')
            
            return matches
            
        except Exception as e:
            logger.error(f"LLM resolution failed: {e}")
            # Return empty matches on failure
            return {term: EntityMatch(term, None, 0.0, 'llm_error') 
                    for term in terms}
    
    def _call_llm_with_retry(self, messages, max_retries=3, **kwargs):
        """Call LLM with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return self.llm_client.chat.completions.create(
                    model=settings.openrouter_model,
                    messages=messages,
                    **kwargs
                )
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                    logger.warning(
                        f"LLM call failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM call failed after {max_retries} attempts: {e}")
        
        raise last_exception
    
    def get_resolution_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_resolutions = sum([
            self._resolution_stats['exact_matches'],
            self._resolution_stats['vector_matches'],
            self._resolution_stats['fuzzy_matches'],
            self._resolution_stats['llm_matches'],
            self._resolution_stats['no_matches']
        ])
        
        if total_resolutions > 0:
            success_rate = 1 - (self._resolution_stats['no_matches'] / total_resolutions)
        else:
            success_rate = 0
        
        return {
            **self._resolution_stats,
            'total_resolutions': total_resolutions,
            'success_rate': success_rate,
            'cache_hit_rate': self._resolution_stats['cache_hits'] / 
                             max(1, self._resolution_stats['cache_hits'] + 
                                 self._resolution_stats['cache_misses'])
        }