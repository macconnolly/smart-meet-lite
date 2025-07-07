#!/usr/bin/env python3
"""Test that enhanced extraction results are saved to the database."""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our components
from src.processor import MeetingProcessor
from src.models import Meeting
from src.database import get_db
from src.qdrant_store import QdrantStore
from src.embeddings import EmbeddingEngine
from src.config import settings
from openai import OpenAI

# Test transcript
TEST_TRANSCRIPT = """
Sarah (Project Manager): Good morning everyone. Let's start with a quick status update on the mobile app redesign project.

Mike (Lead Developer): The API integration is complete and tested. We're now working on the UI components for the dashboard.

Sarah: Excellent. What about the user authentication feature?

Mike: That's in progress. We should have it ready by Friday. John is leading that effort.

John (Senior Developer): Yes, I'm implementing OAuth2 with support for Google and Apple sign-in. Currently blocked on getting the Apple developer certificates.

Sarah: I'll follow up with IT to expedite that. Let's make that a high priority action item.

Decision: We'll proceed with OAuth2 implementation for user authentication, supporting both Google and Apple sign-in.

Emily (UX Designer): I've completed the mockups for the new onboarding flow. I'll share them after this meeting.

Sarah: Great. Any other blockers or concerns?

Mike: We need to decide on the analytics provider. It's blocking the metrics dashboard implementation.

Sarah: Let's go with Mixpanel based on our previous evaluation. I'll create the account today.

Action items:
1. Sarah to follow up with IT on Apple developer certificates - High priority
2. Emily to share onboarding mockups with the team
3. Sarah to create Mixpanel account for analytics
"""

async def test_enhanced_db_save():
    """Test that enhanced extraction saves to database."""
    print("Testing Enhanced Extraction Database Save")
    print("=" * 50)
    
    # Initialize components
    db = next(get_db())
    qdrant = QdrantStore()
    embeddings = EmbeddingEngine()
    
    # Create OpenAI client for processor
    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1"
    )
    
    processor = MeetingProcessor(db, qdrant, embeddings, client)
    
    # Create meeting
    meeting = Meeting(
        id=f"test-enhanced-db-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        title="Mobile App Redesign Status Update",
        date=datetime.now(),
        transcript=TEST_TRANSCRIPT,
        email_metadata={
            "from": "sarah@company.com",
            "to": ["mike@company.com", "john@company.com", "emily@company.com"],
            "subject": "Mobile App Redesign Status Update"
        }
    )
    
    print(f"Created meeting: {meeting.id}")
    
    # Process the meeting
    print("\nProcessing meeting with enhanced extraction...")
    try:
        result = await processor.process_meeting(meeting)
        
        print(f"\n✓ Processing complete!")
        print(f"  - Memories: {result['memory_count']}")
        print(f"  - Entities: {result['entity_count']}")
        print(f"  - Relationships: {result['relationship_count']}")
        print(f"  - State changes: {result['state_change_count']}")
        
        # Check what was saved to the database
        print("\nVerifying database contents...")
        
        # Check memories in SQLite
        from src.models import Memory
        memories = db.query(Memory).filter(Memory.meeting_id == meeting.id).all()
        print(f"\nMemories in SQLite: {len(memories)}")
        for i, memory in enumerate(memories[:3]):
            print(f"  {i+1}. {memory.content[:80]}...")
        
        # Check entities
        from src.models import Entity
        entities = db.query(Entity).all()
        recent_entities = sorted(entities, key=lambda e: e.created_at or datetime.min, reverse=True)[:5]
        print(f"\nRecent entities in database:")
        for entity in recent_entities:
            print(f"  - {entity.name} ({entity.type}) - Status: {entity.current_state.get('status', 'N/A') if entity.current_state else 'N/A'}")
        
        # Check Qdrant
        try:
            qdrant_count = qdrant.client.count(
                collection_name=settings.qdrant_collection,
                count_filter={"must": [{"key": "meeting_id", "match": {"value": meeting.id}}]}
            )
            print(f"\nMemories in Qdrant: {qdrant_count.count}")
        except Exception as e:
            print(f"\nCould not check Qdrant: {e}")
        
        # Check if we used enhanced extraction
        if result.get('extraction_metadata'):
            metadata = result['extraction_metadata']
            if metadata.get('extraction_method') == 'basic_fallback':
                print("\n⚠️  WARNING: Fell back to basic extraction")
                print(f"   Reason: {metadata.get('extraction_error', 'Unknown')}")
            else:
                print("\n✅ Successfully used enhanced extraction!")
                if metadata.get('meeting_type'):
                    print(f"   Meeting type: {metadata['meeting_type']}")
                if metadata.get('deliverables'):
                    print(f"   Deliverables found: {len(metadata['deliverables'])}")
                if metadata.get('stakeholder_intelligence'):
                    print(f"   Stakeholder intelligence: {len(metadata['stakeholder_intelligence'])}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Processing failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_db_save())
    exit(0 if success else 1)