#!/usr/bin/env python3
"""Test the enhanced extractor with OpenRouter structured output."""

import json
import os
from dotenv import load_dotenv
from src.extractor_enhanced import EnhancedMeetingExtractor
from openai import OpenAI

# Load environment variables
load_dotenv()

# Test transcript
test_transcript = """
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

def test_extraction():
    """Test the enhanced extraction."""
    try:
        # Create extractor with OpenAI client (though it uses requests internally)
        client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
        
        extractor = EnhancedMeetingExtractor(client)
        
        print("Testing enhanced extraction with simplified schema...")
        result = extractor.extract(test_transcript, "test-meeting-001")
        
        print("\n✅ Extraction successful!")
        print(f"\nSummary: {result.summary}")
        print(f"\nParticipants: {', '.join(result.participants)}")
        print(f"\nTopics: {', '.join(result.topics)}")
        
        print(f"\nDecisions ({len(result.decisions)}):")
        for decision in result.decisions:
            print(f"  - {decision}")
        
        print(f"\nAction Items ({len(result.action_items)}):")
        for item in result.action_items:
            if isinstance(item, dict):
                print(f"  - {item.get('description', item.get('action', str(item)))}")
            else:
                print(f"  - {item}")
        
        print(f"\nEntities found ({len(result.entities)}):")
        for entity in result.entities[:5]:  # Show first 5
            print(f"  - {entity['name']} ({entity['type']})")
        
        print(f"\nRelationships ({len(result.relationships)}):")
        for rel in result.relationships[:5]:  # Show first 5
            print(f"  - {rel['from']} {rel['type']} {rel['to']}")
        
        print(f"\nMemories ({len(result.memories)}):")
        for memory in result.memories[:3]:  # Show first 3
            print(f"  - {memory.content[:100]}...")
        
        # Show metadata
        print(f"\nMetadata keys: {list(result.meeting_metadata.keys())}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Extraction failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_extraction()
    exit(0 if success else 1)