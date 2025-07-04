"""
Centralized LLM processor with batching, caching, and fallback support.
Handles all LLM interactions for the system.
"""

import asyncio
import json
import logging
import httpx
from typing import List, Dict, Any, Tuple, Optional
from openai import OpenAI

from src.cache import CacheLayer
from src.config import settings

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    A centralized processor for all LLM interactions, featuring batching,
    caching, and resilience for state comparison and entity extraction.
    """
    
    # Model fallback chain - ordered by preference
    MODELS = [
        "openrouter/cypher-alpha:free",       # Fast and free
        "openai/gpt-4-turbo-preview",         # Good alternative
        "openai/gpt-3.5-turbo",               # Fast and reliable
        "mistralai/mixtral-8x7b-instruct"     # Open source fallback
    ]
    
    def __init__(self, cache_layer: CacheLayer):
        """
        Initialize LLM processor with cache.
        
        Args:
            cache_layer: Cache instance for storing results
        """
        self.cache = cache_layer
        
        # Setup proxy configuration for corporate environments
        proxies = None
        if settings.https_proxy or settings.http_proxy:
            proxies = {}
            if settings.http_proxy:
                proxies["http://"] = settings.http_proxy
            if settings.https_proxy:
                proxies["https://"] = settings.https_proxy
            logger.info(f"Using proxy configuration: {proxies}")
        
        # Create HTTP client with proxy and SSL configuration
        http_client = httpx.Client(
            verify=settings.ssl_verify,
            proxies=proxies,
            timeout=30.0  # 30 second timeout
        )
        
        self.client = OpenAI(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            http_client=http_client
        )
        self._fallback_count = 0
        
    async def compare_states_batch(
        self, 
        state_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Compares a batch of old/new state pairs using a single LLM call.
        
        Args:
            state_pairs: List of (old_state, new_state) tuples
            
        Returns:
            List of comparison results with 'has_changes' and 'reason'
        """
        if not state_pairs:
            return []
            
        # Check cache first
        cached_results = []
        uncached_indices = []
        
        for i, (old_state, new_state) in enumerate(state_pairs):
            cache_key = self.cache.make_key("compare", old_state, new_state)
            cached = self.cache.get(cache_key)
            
            if cached is not None:
                cached_results.append((i, cached))
            else:
                uncached_indices.append(i)
                
        # If all results are cached, return them
        if not uncached_indices:
            return [result for _, result in sorted(cached_results)]
            
        # Get uncached pairs
        uncached_pairs = [state_pairs[i] for i in uncached_indices]
        
        # Build batch comparison prompt
        prompt = self._build_batch_comparison_prompt(uncached_pairs)
        
        try:
            # Try LLM comparison with fallback
            llm_response = await self._call_with_fallback(
                prompt,
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse response
            results = self._parse_batch_response(llm_response, uncached_pairs)
            
            # Cache results
            for i, (old_state, new_state) in enumerate(uncached_pairs):
                cache_key = self.cache.make_key("compare", old_state, new_state)
                self.cache.set(cache_key, results[i], ttl=3600)  # 1 hour cache
                
            # Merge cached and new results
            all_results = cached_results + [(uncached_indices[i], results[i]) 
                                           for i in range(len(results))]
            
            # Sort by original index and return
            return [result for _, result in sorted(all_results)]
            
        except Exception as e:
            logger.error(f"Batch comparison failed: {e}")
            # Fallback to simple comparison
            return [self._simple_comparison(p[0], p[1]) for p in state_pairs]
            
    async def _call_with_fallback(self, prompt: str, **kwargs) -> str:
        """
        Call LLM with automatic model fallback on failure.
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the API call
            
        Returns:
            The LLM response content
            
        Raises:
            Exception: If all models fail
        """
        for i, model in enumerate(self.MODELS):
            try:
                # Adjust parameters for model compatibility
                api_kwargs = kwargs.copy()
                
                # Remove response_format for models that don't support it
                if "anthropic" in model or "mistral" in model:
                    if "response_format" in api_kwargs:
                        del api_kwargs["response_format"]
                        # Add JSON instruction to prompt for these models
                        system_prompt = "You must respond with valid JSON only. No other text."
                else:
                    system_prompt = "You are a helpful assistant that responds in JSON."
                
                # Make the API call
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    **api_kwargs
                )
                
                content = response.choices[0].message.content
                
                # Validate JSON response
                if "anthropic" in model or "mistral" in model:
                    # These models might wrap JSON in markdown
                    if "```json" in content:
                        import re
                        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                        if json_match:
                            content = json_match.group(1)
                
                # Test that it's valid JSON
                json.loads(content)
                
                if i > 0:
                    logger.info(f"Succeeded with fallback model: {model}")
                    self._fallback_count += 1
                    
                return content
                
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}")
                if i == len(self.MODELS) - 1:
                    raise Exception(f"All LLM models failed. Last error: {e}")
                    
    def _build_batch_comparison_prompt(self, pairs: List[Tuple[Dict, Dict]]) -> str:
        """Build a prompt for batch state comparison."""
        comparisons = []
        
        for i, (old_state, new_state) in enumerate(pairs):
            comparisons.append(f"""
Comparison {i + 1}:
Previous State: {json.dumps(old_state, indent=2)}
Current State: {json.dumps(new_state, indent=2)}
""")
        
        prompt = f"""Analyze these state comparisons and identify ALL changes.

{chr(10).join(comparisons)}

For each comparison, determine:
1. Whether any fields have changed (not just exact match, but semantic changes too)
2. What specific fields changed
3. A clear, concise reason for the change

Important:
- "planning" → "in planning phase" is NOT a change
- "30%" → "30% complete" is NOT a change  
- But "30%" → "50%" IS a change
- New fields added or fields removed are changes
- Look for semantic differences, not just string differences

Return a JSON object with a "comparisons" array:
{{
  "comparisons": [
    {{
      "index": 1,
      "has_changes": true/false,
      "changed_fields": ["field1", "field2"],
      "reason": "Clear description of what changed"
    }},
    ...
  ]
}}
"""
        return prompt
        
    def _parse_batch_response(self, response: str, pairs: List[Tuple[Dict, Dict]]) -> List[Dict[str, Any]]:
        """Parse the batch comparison response from LLM."""
        try:
            data = json.loads(response)
            comparisons = data.get("comparisons", [])
            
            # Map results by index
            results_map = {comp["index"]: comp for comp in comparisons}
            
            # Build results in order
            results = []
            for i in range(len(pairs)):
                if i + 1 in results_map:
                    comp = results_map[i + 1]
                    results.append({
                        "has_changes": comp.get("has_changes", False),
                        "changed_fields": comp.get("changed_fields", []),
                        "reason": comp.get("reason", "State updated")
                    })
                else:
                    # Fallback if comparison missing
                    results.append(self._simple_comparison(pairs[i][0], pairs[i][1]))
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to parse batch response: {e}")
            # Fallback to simple comparison for all
            return [self._simple_comparison(p[0], p[1]) for p in pairs]
            
    def _simple_comparison(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        """Simple field-by-field comparison as fallback."""
        changed_fields = []
        
        # Check for changed/added fields
        for key, new_value in new_state.items():
            if key not in old_state:
                changed_fields.append(key)
            elif old_state[key] != new_value:
                changed_fields.append(key)
                
        # Check for removed fields
        for key in old_state:
            if key not in new_state:
                changed_fields.append(key)
                
        has_changes = len(changed_fields) > 0
        
        # Generate simple reason
        if not has_changes:
            reason = "No changes detected"
        elif len(changed_fields) == 1:
            field = changed_fields[0]
            if field in new_state:
                reason = f"{field} updated to {new_state[field]}"
            else:
                reason = f"{field} was removed"
        else:
            reason = f"Multiple fields changed: {', '.join(changed_fields)}"
            
        return {
            "has_changes": has_changes,
            "changed_fields": changed_fields,
            "reason": reason
        }
        
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            "cache_stats": self.cache.stats(),
            "fallback_count": self._fallback_count,
            "models_available": len(self.MODELS)
        }
    
    def test_connectivity(self) -> Dict[str, Any]:
        """Test connectivity to each model for diagnostics."""
        results = {}
        for model in self.MODELS:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=10
                )
                results[model] = {"status": "success", "response": response.choices[0].message.content}
                logger.info(f"✓ {model} connectivity OK")
            except Exception as e:
                results[model] = {"status": "failed", "error": str(e)}
                logger.error(f"✗ {model} connectivity FAILED: {e}")
        return results