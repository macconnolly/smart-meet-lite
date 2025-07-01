#!/usr/bin/env python3
"""Comprehensive system test with fresh ingestion and queries."""

import time
import json
import requests
from datetime import datetime
from typing import Dict, Any, List

API_URL = "http://localhost:8000/api"

# Sample meeting transcript for testing
TEST_TRANSCRIPT = """
Meeting: Q4 Planning Session
Date: January 15, 2025
Participants: Sarah Chen (VP Engineering), Mike Johnson (Product Manager), Lisa Park (Tech Lead)

Sarah: Good morning everyone. Let's discuss our Q4 roadmap and the mobile app redesign project.

Mike: Thanks Sarah. The mobile app redesign is critical for our Q4 goals. We need to modernize the UI and improve performance. The current app has a 2.5 star rating.

Lisa: I agree. My team has been analyzing the performance bottlenecks. The main issues are the legacy API calls and the outdated React Native version. We should upgrade to React Native 0.72.

Sarah: What's the timeline for this project, Mike?

Mike: We need to complete Phase 1 by end of February. That includes the new UI design and basic performance improvements. Lisa, can your team handle that?

Lisa: Yes, but we'll need two additional developers. The current team is already working on the payment system integration.

Sarah: I'll approve the additional headcount. What about the backend changes?

Lisa: The backend team needs to optimize the user data queries. Currently, profile loading takes 8-10 seconds. We're targeting under 2 seconds.

Mike: That's crucial. Our user research shows that slow loading is the #1 complaint. 

Sarah: Let's set up weekly sync meetings to track progress. Mike, you'll own the product requirements. Lisa, you'll own the technical implementation. I'll handle stakeholder communication.

Mike: Sounds good. I'll have the updated PRD ready by Thursday.

Lisa: I'll create the technical design document and share it by Friday. We should also plan for a security review.

Sarah: Excellent. Let's make this our top priority for Q4. Any blockers we should discuss?

Lisa: We need to finalize the API deprecation strategy. Some enterprise customers still use v1 endpoints.

Mike: I'll coordinate with the customer success team to create a migration plan.

Sarah: Perfect. Let's reconvene next Monday to review the documents. Thanks everyone.
"""

def ingest_test_meeting() -> Dict[str, Any]:
    """Ingest a test meeting and measure performance."""
    print("\n1. INGESTING TEST MEETING")
    print("-" * 60)
    
    start_time = time.perf_counter()
    
    response = requests.post(
        f"{API_URL}/ingest",
        json={
            "transcript": TEST_TRANSCRIPT,
            "title": "Q4 Planning Session - Mobile App Redesign",
            "participants": ["Sarah Chen", "Mike Johnson", "Lisa Park"],
            "date": datetime.now().isoformat()
        }
    )
    
    end_time = time.perf_counter()
    elapsed = end_time - start_time
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Ingestion successful in {elapsed:.2f} seconds")
        print(f"  - Meeting ID: {result.get('meeting_id', result.get('id', 'N/A'))}")
        print(f"  - Memories created: {result.get('memories_created', len(result.get('memories', [])))}")
        print(f"  - Entities found: {result.get('entities_found', len(result.get('entities', [])))}")
        print(f"  - Relationships: {result.get('relationships_created', len(result.get('relationships', [])))}")
        return {
            "success": True,
            "time": elapsed,
            "result": result
        }
    else:
        print(f"✗ Ingestion failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return {
            "success": False,
            "time": elapsed,
            "error": response.text
        }

def test_queries() -> List[Dict[str, Any]]:
    """Test various query types and measure performance."""
    print("\n2. TESTING QUERIES")
    print("-" * 60)
    
    test_queries = [
        # Entity status queries
        "What's the status of the mobile app redesign?",
        "What is Lisa Park working on?",
        
        # Ownership queries
        "Who owns the technical implementation?",
        "Who is responsible for stakeholder communication?",
        
        # Timeline queries
        "What are the deadlines for Phase 1?",
        "When will the PRD be ready?",
        
        # Relationship queries
        "What is Mike Johnson's role in the mobile app redesign?",
        "What blockers were discussed?",
        
        # Complex queries
        "What are all the deliverables mentioned and who owns them?",
        "What performance improvements are planned?"
    ]
    
    results = []
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nQuery {i}: {query}")
        
        start_time = time.perf_counter()
        
        response = requests.post(
            f"{API_URL}/query",
            json={"query": query}
        )
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Response in {elapsed:.2f} seconds")
            print(f"  Intent: {result.get('intent', {}).get('intent_type', 'unknown')}")
            print(f"  Entities: {len(result.get('entities_involved', []))}")
            
            # Show answer preview
            answer = result.get('answer', '')
            if len(answer) > 150:
                answer = answer[:147] + "..."
            print(f"  Answer: {answer}")
            
            results.append({
                "query": query,
                "success": True,
                "time": elapsed,
                "result": result
            })
        else:
            print(f"✗ Query failed: {response.status_code}")
            results.append({
                "query": query,
                "success": False,
                "time": elapsed,
                "error": response.text
            })
        
        time.sleep(0.5)  # Small delay between queries
    
    return results

def test_entity_search() -> Dict[str, Any]:
    """Test entity search performance."""
    print("\n3. TESTING ENTITY SEARCH")
    print("-" * 60)
    
    search_terms = ["mobile", "Lisa", "app", "performance"]
    
    total_time = 0
    for term in search_terms:
        print(f"\nSearching for entities matching '{term}':")
        
        start_time = time.perf_counter()
        
        response = requests.get(
            f"{API_URL}/entities",
            params={"search": term, "limit": 10}
        )
        
        end_time = time.perf_counter()
        elapsed = end_time - start_time
        total_time += elapsed
        
        if response.status_code == 200:
            entities = response.json()
            print(f"✓ Found {len(entities)} entities in {elapsed:.2f} seconds")
            for entity in entities[:3]:  # Show first 3
                print(f"  - {entity['name']} ({entity['type']})")
        else:
            print(f"✗ Search failed: {response.status_code}")
    
    return {
        "avg_time": total_time / len(search_terms),
        "total_searches": len(search_terms)
    }

def main():
    """Run comprehensive system test."""
    print("=" * 80)
    print("SMART-MEET LITE COMPREHENSIVE SYSTEM TEST")
    print("Testing with Qdrant Entity Embeddings")
    print("=" * 80)
    
    # Test 1: Ingestion
    ingestion_result = ingest_test_meeting()
    
    if not ingestion_result["success"]:
        print("\n❌ Ingestion failed, cannot continue with tests")
        return
    
    # Wait a bit for background processing
    print("\nWaiting 3 seconds for background processing...")
    time.sleep(3)
    
    # Test 2: Queries
    query_results = test_queries()
    
    # Test 3: Entity Search
    search_result = test_entity_search()
    
    # Summary
    print("\n" + "=" * 80)
    print("PERFORMANCE SUMMARY")
    print("=" * 80)
    
    # Ingestion metrics
    print(f"\nIngestion Performance:")
    print(f"  Time: {ingestion_result['time']:.2f} seconds")
    print(f"  Entities: {ingestion_result['result'].get('entities_found', 'N/A')}")
    print(f"  Relationships: {ingestion_result['result'].get('relationships_created', 'N/A')}")
    
    # Query metrics
    successful_queries = [r for r in query_results if r["success"]]
    failed_queries = [r for r in query_results if not r["success"]]
    query_times = [r["time"] for r in successful_queries]
    
    print(f"\nQuery Performance:")
    print(f"  Total queries: {len(query_results)}")
    print(f"  Successful: {len(successful_queries)}")
    print(f"  Failed: {len(failed_queries)}")
    if query_times:
        print(f"  Average time: {sum(query_times)/len(query_times):.2f} seconds")
        print(f"  Min time: {min(query_times):.2f} seconds")
        print(f"  Max time: {max(query_times):.2f} seconds")
    
    # Entity search metrics
    print(f"\nEntity Search Performance:")
    print(f"  Average time: {search_result['avg_time']:.2f} seconds")
    
    # Overall assessment
    print("\n" + "-" * 80)
    print("PERFORMANCE ASSESSMENT")
    print("-" * 80)
    
    if query_times:
        avg_query_time = sum(query_times)/len(query_times)
        if avg_query_time < 5:
            print("✅ Query performance: EXCELLENT (<5 seconds average)")
        elif avg_query_time < 10:
            print("⚠️  Query performance: GOOD (5-10 seconds average)")
        else:
            print("❌ Query performance: NEEDS IMPROVEMENT (>10 seconds average)")
    
    # Comparison with old system
    print("\n" + "-" * 80)
    print("COMPARISON WITH OLD SYSTEM")
    print("-" * 80)
    print("Old system: 135+ seconds per query, 0% success rate")
    if query_times:
        print(f"New system: {sum(query_times)/len(query_times):.2f} seconds average, {len(successful_queries)/len(query_results)*100:.0f}% success rate")
        improvement = 135 / (sum(query_times)/len(query_times))
        print(f"Performance improvement: {improvement:.1f}x faster")

if __name__ == "__main__":
    main()