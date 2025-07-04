#!/usr/bin/env python3
"""
Test the state tracking fix to ensure post-processing correctly detects state changes.
This test simulates a realistic sequence of meetings where entities change states.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage import MemoryStorage as Storage
from src.embeddings import EmbeddingEngine as LocalEmbeddings
from src.processor import MeetingProcessor
from src.entity_resolver import EntityResolver
from src.config import Settings
from src.models import Meeting, EntityState
from src.extractor_enhanced import EnhancedMeetingExtractor
from dotenv import load_dotenv
import os

load_dotenv()

# Test meeting sequence with state changes
TEST_MEETINGS = [
    {
        "date": "2024-01-01",
        "transcript": """
        Meeting with project team to discuss Q1 initiatives.
        
        John Smith will be leading the mobile app redesign project starting next week.
        The project is currently in planning phase.
        
        Sarah Johnson is working on the API migration which is planned but not started yet.
        
        The customer portal project is blocked waiting for vendor quotes.
        Mike Chen is the owner of this project.
        """,
        "expected_states": {
            "John Smith": "planned",
            "mobile app redesign": "planned",
            "Sarah Johnson": "active",
            "API migration": "planned",
            "customer portal": "blocked",
            "Mike Chen": "active"
        }
    },
    {
        "date": "2024-01-08",
        "transcript": """
        Weekly sync meeting updates:
        
        John Smith has started the mobile app redesign project. The team is now actively working on wireframes.
        
        Sarah Johnson reports the API migration is now in progress. She's completed the initial assessment.
        
        Good news - Mike Chen got the vendor quotes and the customer portal project is now unblocked and in progress.
        """,
        "expected_states": {
            "John Smith": "active",
            "mobile app redesign": "in_progress",
            "Sarah Johnson": "active", 
            "API migration": "in_progress",
            "customer portal": "in_progress",
            "Mike Chen": "active"
        },
        "expected_transitions": {
            "mobile app redesign": ("planned", "in_progress"),
            "API migration": ("planned", "in_progress"),
            "customer portal": ("blocked", "in_progress")
        }
    },
    {
        "date": "2024-01-15",
        "transcript": """
        Status update meeting:
        
        The mobile app redesign hit a blocker - John Smith discovered we need new licensing for the design tools.
        
        Sarah Johnson is making good progress on the API migration. Still in progress.
        
        Mike Chen completed the first phase of the customer portal! Moving to phase 2 next week.
        """,
        "expected_states": {
            "mobile app redesign": "blocked",
            "API migration": "in_progress",
            "customer portal": "completed"
        },
        "expected_transitions": {
            "mobile app redesign": ("in_progress", "blocked"),
            "customer portal": ("in_progress", "completed")
        }
    }
]

async def test_state_tracking():
    """Test the complete state tracking flow with realistic meeting sequences."""
    
    print("🧪 Testing State Tracking Post-Processing Fix\n")
    
    # Initialize components
    settings = Settings()
    storage = Storage(settings.database_path)
    embeddings = LocalEmbeddings(settings.model_path)
    
    # Initialize LLM client
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return
    
    from httpx import AsyncClient
    from openai import OpenAI
    http_client = AsyncClient(timeout=30.0)
    
    llm_client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Smart-Meet Lite"
        },
        http_client=http_client
    )
    
    # Create shared entity resolver
    entity_resolver = EntityResolver(
        storage=storage,
        embeddings=embeddings,
        llm_client=llm_client,
        use_llm=settings.entity_resolution_use_llm
    )
    
    # Initialize processor and extractor
    processor = MeetingProcessor(
        storage=storage,
        entity_resolver=entity_resolver,
        embeddings=embeddings
    )
    
    extractor = EnhancedMeetingExtractor(llm_client)
    
    # Track results
    results = {
        "meetings_processed": 0,
        "entities_created": 0,
        "states_detected": 0,
        "transitions_detected": 0,
        "expected_transitions": 0,
        "missed_transitions": [],
        "incorrect_states": []
    }
    
    try:
        # Process each test meeting
        for i, test_meeting in enumerate(TEST_MEETINGS):
            print(f"\n📅 Processing Meeting {i+1} - {test_meeting['date']}")
            print("-" * 50)
            
            # Create meeting record
            meeting = Meeting(
                id=f"test-meeting-{i+1}",
                title=f"Test Meeting {i+1}",
                date=datetime.fromisoformat(test_meeting['date']),
                raw_transcript=test_meeting['transcript']
            )
            storage.save_meeting(meeting)
            
            # Extract entities and metadata
            print("🤖 Extracting entities and states...")
            extraction = await extractor.extract(
                test_meeting['transcript'],
                meeting.id,
                email_metadata={
                    "date": test_meeting['date'],
                    "subject": f"Test Meeting {i+1}"
                }
            )
            
            # Process the extraction
            print("⚙️  Processing entities and detecting state changes...")
            processed = await processor.process_meeting(extraction, meeting.id)
            
            results["meetings_processed"] += 1
            results["entities_created"] += len(processed["entities"])
            
            # Check current states
            print("\n📊 Current States:")
            for entity_name, expected_state in test_meeting.get("expected_states", {}).items():
                entity = storage.get_entity_by_name(entity_name)
                if entity:
                    current_states = storage.get_entity_current_state(entity.id)
                    if current_states:
                        actual_state = current_states[0].state
                        status = "✅" if actual_state == expected_state else "❌"
                        print(f"  {status} {entity_name}: {actual_state} (expected: {expected_state})")
                        if actual_state != expected_state:
                            results["incorrect_states"].append({
                                "meeting": i+1,
                                "entity": entity_name,
                                "expected": expected_state,
                                "actual": actual_state
                            })
                    else:
                        print(f"  ❓ {entity_name}: No state found")
                else:
                    print(f"  ❓ {entity_name}: Entity not found")
            
            # Check state transitions
            if "expected_transitions" in test_meeting:
                print("\n🔄 State Transitions:")
                for entity_name, (from_state, to_state) in test_meeting["expected_transitions"].items():
                    entity = storage.get_entity_by_name(entity_name)
                    if entity:
                        # Get all states for this entity
                        all_states = storage.get_entity_timeline(entity.id)
                        
                        # Look for the transition
                        found_transition = False
                        for j in range(1, len(all_states)):
                            if (all_states[j-1].state == from_state and 
                                all_states[j].state == to_state and
                                all_states[j].meeting_id == meeting.id):
                                found_transition = True
                                results["transitions_detected"] += 1
                                print(f"  ✅ {entity_name}: {from_state} → {to_state}")
                                break
                        
                        if not found_transition:
                            results["missed_transitions"].append({
                                "meeting": i+1,
                                "entity": entity_name,
                                "expected": f"{from_state} → {to_state}"
                            })
                            print(f"  ❌ {entity_name}: Expected {from_state} → {to_state} NOT FOUND")
                        
                        results["expected_transitions"] += 1
            
            # Show summary of this meeting
            print(f"\n📈 Meeting Summary:")
            print(f"  - Entities processed: {len(processed['entities'])}")
            print(f"  - State changes detected: {len(processed.get('state_changes', []))}")
            
            results["states_detected"] += len(processed.get('state_changes', []))
            
            # Small delay between meetings
            await asyncio.sleep(0.5)
        
        # Final summary
        print("\n" + "=" * 60)
        print("🏁 FINAL TEST RESULTS")
        print("=" * 60)
        print(f"✅ Meetings processed: {results['meetings_processed']}")
        print(f"✅ Entities created: {results['entities_created']}")
        print(f"✅ States detected: {results['states_detected']}")
        print(f"✅ Transitions detected: {results['transitions_detected']}/{results['expected_transitions']}")
        
        if results['missed_transitions']:
            print(f"\n❌ Missed Transitions ({len(results['missed_transitions'])}):")
            for miss in results['missed_transitions']:
                print(f"   - Meeting {miss['meeting']}: {miss['entity']} - {miss['expected']}")
        
        if results['incorrect_states']:
            print(f"\n❌ Incorrect States ({len(results['incorrect_states'])}):")
            for incorrect in results['incorrect_states']:
                print(f"   - Meeting {incorrect['meeting']}: {incorrect['entity']} - "
                      f"got '{incorrect['actual']}', expected '{incorrect['expected']}'")
        
        # Overall verdict
        success = (results['transitions_detected'] == results['expected_transitions'] and
                   len(results['incorrect_states']) == 0)
        
        print("\n" + "=" * 60)
        if success:
            print("✅ STATE TRACKING IS WORKING CORRECTLY!")
            print("   Post-processing successfully detects state changes")
        else:
            print("❌ STATE TRACKING HAS ISSUES")
            print(f"   - Detected {results['transitions_detected']}/{results['expected_transitions']} transitions")
            print(f"   - {len(results['incorrect_states'])} incorrect states")
        print("=" * 60)
        
        # Show some actual database records
        print("\n📋 Sample Database Records:")
        print("\nEntity States (last 10):")
        with storage._get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.name, es.state, es.confidence, es.meeting_id, es.timestamp
                FROM entity_states es
                JOIN entities e ON es.entity_id = e.id
                ORDER BY es.timestamp DESC
                LIMIT 10
            """)
            for row in cursor.fetchall():
                print(f"  - {row[0]}: {row[1]} (conf: {row[2]:.2f}) @ {row[3]} [{row[4]}]")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await http_client.aclose()

if __name__ == "__main__":
    asyncio.run(test_state_tracking())