"""Test the extraction functionality directly."""

from src.extractor import MemoryExtractor
from src.config import settings

# Simple test transcript
test_transcript = """
Sarah: Let's review our Q2 goals. The mobile app redesign is our top priority.
Mike: I'll take ownership of the API optimization. We need to get response times under 1 second.
Lisa: I'm working on the new UI mockups. Should have them ready by end of week.
Sarah: Great. Let's make these decisions official:
1. Mike owns API optimization with a target of sub-1 second response times
2. Lisa owns UI design with mockups due Friday
3. We're targeting end of Q2 for the full release
Mike: I'll need to coordinate with the billing team on the API changes.
Lisa: And I'll need user feedback sessions scheduled for next week.
Sarah: Approved. Let's meet again next Monday to review progress.
"""


def test_extraction():
    """Test the extraction with a simple transcript."""
    print("Testing extraction...")
    print(f"Using model: {settings.openrouter_model}")
    print(f"API key present: {'Yes' if settings.openrouter_api_key else 'No'}")
    print(
        f"API key length: {len(settings.openrouter_api_key) if settings.openrouter_api_key else 0}"
    )

    extractor = MemoryExtractor()

    try:
        result = extractor.extract(test_transcript, "test-meeting-123")

        print("\n✓ Extraction successful!")
        print(f"  - Memories: {len(result.memories)}")
        print(f"  - Entities: {len(result.entities)}")
        print(f"  - Participants: {result.participants}")
        print(f"  - Decisions: {len(result.decisions)}")
        print(f"  - Action Items: {len(result.action_items)}")

        if result.decisions:
            print("\nDecisions extracted:")
            for i, decision in enumerate(result.decisions, 1):
                print(f"  {i}. {decision}")

        if result.action_items:
            print("\nAction items extracted:")
            for i, item in enumerate(result.action_items, 1):
                assignee = item.get("assignee", "Unassigned")
                due = item.get("due", "No deadline")
                print(f"  {i}. {item['action']} (Assignee: {assignee}, Due: {due})")

        if result.entities:
            print("\nEntities found:")
            for entity in result.entities:
                print(f"  - {entity['name']} ({entity['type']})")

    except Exception as e:
        print(f"\n✗ Extraction failed: {e}")
        print(f"Error type: {type(e).__name__}")

        # Try to get more details
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_extraction()
