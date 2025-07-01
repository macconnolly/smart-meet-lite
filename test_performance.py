#!/usr/bin/env python3
"""Test query performance after entity embeddings migration."""

import time
import json
import requests
from typing import Dict, Any

API_URL = "http://localhost:8000/api"

def time_query(query: str) -> Dict[str, Any]:
    """Execute a query and measure response time."""
    print(f"\nQuery: {query}")
    print("-" * 50)
    
    start_time = time.perf_counter()
    
    response = requests.post(
        f"{API_URL}/query",
        json={"query": query}
    )
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Success in {elapsed:.2f} seconds")
        print(f"Intent: {result.get('intent', {}).get('intent_type', 'unknown')}")
        print(f"Entities found: {len(result.get('entities_involved', []))}")
        return {
            "success": True,
            "time": elapsed,
            "result": result
        }
    else:
        print(f"✗ Failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return {
            "success": False,
            "time": elapsed,
            "error": response.text
        }

def main():
    """Run performance tests."""
    print("=" * 60)
    print("Smart-Meet Lite Performance Test")
    print("Testing entity resolution with Qdrant")
    print("=" * 60)
    
    # Test queries that require entity resolution
    test_queries = [
        # Status queries
        "What's the status of the UAT project?",
        "What is Prashant working on?",
        "What's the current state of the BRV system?",
        
        # Ownership queries
        "Who owns the ITLT Review Sessions?",
        "Who is responsible for business managed apps?",
        
        # Timeline queries
        "What deadlines are coming up next week?",
        "What changed in the last meeting?",
        
        # Complex queries
        "What are all the projects Steve is working on and their current status?",
        "Which systems are transitioning from Honeywell to Solstice?",
    ]
    
    results = []
    total_time = 0
    
    for query in test_queries:
        result = time_query(query)
        results.append(result)
        total_time += result["time"]
        time.sleep(0.5)  # Small delay between queries
    
    # Summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["success"])
    print(f"\nQueries executed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"\nTotal time: {total_time:.2f} seconds")
    print(f"Average time per query: {total_time/len(results):.2f} seconds")
    
    # Performance comparison
    print("\n" + "-" * 60)
    print("PERFORMANCE IMPROVEMENT")
    print("-" * 60)
    print("Before migration: 135+ seconds per query")
    print(f"After migration: {total_time/len(results):.2f} seconds per query")
    print(f"Improvement: {135/(total_time/len(results)):.1f}x faster!")
    
    # Detailed results
    print("\n" + "-" * 60)
    print("DETAILED RESULTS")
    print("-" * 60)
    
    for i, (query, result) in enumerate(zip(test_queries, results)):
        print(f"\n{i+1}. {query}")
        print(f"   Time: {result['time']:.2f}s")
        if result["success"]:
            answer = result["result"].get("answer", "")
            if len(answer) > 100:
                answer = answer[:97] + "..."
            print(f"   Answer: {answer}")
        else:
            print(f"   Error: Failed")

if __name__ == "__main__":
    main()