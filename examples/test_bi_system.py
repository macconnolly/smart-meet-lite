"""Test the business intelligence system."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from src.models import Memory, Meeting, Entity, EntityState, EntityRelationship  # noqa: F401
        print("✓ Models imported")
        from src.config import settings  # noqa: F401
        print("✓ Config imported")
        from src.extractor import MemoryExtractor  # noqa: F401
        print("✓ Extractor imported")
        from src.embeddings import EmbeddingEngine  # noqa: F401
        print("✓ Embeddings imported")
        from src.storage import MemoryStorage  # noqa: F401
        print("✓ Storage imported")
        from src.processor import EntityProcessor  # noqa: F401
        print("✓ Processor imported")
        from src.query_engine import QueryEngine  # noqa: F401
        print("✓ Query engine imported")
        from src.api import app  # noqa: F401
        print("✓ API imported")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_entity_extraction():
    """Test entity extraction from transcript."""
    print("\nTesting entity extraction...")
    try:
        from src.extractor import MemoryExtractor

        extractor = MemoryExtractor()

        # Simple test transcript
        transcript = """
        Sarah: The authentication feature is now complete.
        John: Great! What's next?
        Sarah: I'll start working on the payment system next week.
        John: Perfect. That's a high priority for Q2.
        """

        # Test extraction (without API call for unit test)
        # This will use fallback method
        result = extractor._fallback_extract(transcript, "test-meeting-id")

        print(f"✓ Extracted {len(result.memories)} memories")
        print(f"✓ Found {len(result.entities)} entities")
        print(f"✓ Participants: {', '.join(result.participants)}")

        return True

    except Exception as e:
        print(f"✗ Entity extraction error: {e}")
        return False


def test_entity_processor():
    """Test entity processing logic."""
    print("\nTesting entity processor...")
    try:
        from src.processor import EntityProcessor
        from src.models import EntityType

        processor = EntityProcessor(None)  # Storage not needed for this test

        # Test entity normalization
        assert (
            processor._normalize_name("Authentication Feature")
            == "authentication feature"
        )
        assert processor._normalize_name("Payment System") == "payment system"
        print("✓ Name normalization works")

        # Test entity type validation
        assert processor._validate_entity_type("feature") == EntityType.FEATURE
        assert processor._validate_entity_type("person") == EntityType.PERSON
        print("✓ Entity type validation works")

        # Test change detection
        old_state = {"status": "planned", "progress": 0}
        new_state = {"status": "in_progress", "progress": 20}
        changes = processor._detect_changes(old_state, new_state)
        assert "status" in changes
        assert "progress" in changes
        print("✓ Change detection works")

        return True

    except Exception as e:
        print(f"✗ Entity processor error: {e}")
        return False


def test_query_intent_parsing():
    """Test query intent parsing."""
    print("\nTesting query intent parsing...")
    try:
        from src.query_engine import QueryEngine

        engine = QueryEngine(None, None)  # Dependencies not needed for this test

        # Test fallback intent parsing
        intent1 = engine._fallback_parse_intent("What's the status of Project X?")
        assert intent1.intent_type == "status"
        assert "Project" in intent1.entities
        print("✓ Status query intent detected")

        intent2 = engine._fallback_parse_intent("Who owns the authentication feature?")
        assert intent2.intent_type == "ownership"
        print("✓ Ownership query intent detected")

        intent3 = engine._fallback_parse_intent(
            "How has the project changed over time?"
        )
        assert intent3.intent_type == "timeline"
        print("✓ Timeline query intent detected")

        return True

    except Exception as e:
        print(f"✗ Query intent parsing error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Smart-Meet Lite Business Intelligence Tests")
    print("=" * 60)

    tests = [
        test_imports,
        test_entity_extraction,
        test_entity_processor,
        test_query_intent_parsing,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")

    if passed == len(tests):
        print("\n✓ All tests passed! The business intelligence system is ready.")
        print("\nNext steps:")
        print("1. Make sure .env is configured with OpenRouter API key")
        print("2. Start Qdrant: docker-compose up -d")
        print("3. Run setup: python scripts/setup.py")
        print("4. Start API: python -m src.api")
        print("5. Try the demo: python bi_demo.py")
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")


if __name__ == "__main__":
    main()
