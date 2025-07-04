"""Quick test script to verify the system is working."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from src.models import Memory, Meeting, SearchResult  # noqa: F401
        print("✓ Models imported")
        from src.config import settings  # noqa: F401
        print("✓ Config imported")
        from src.extractor import MemoryExtractor  # noqa: F401
        print("✓ Extractor imported")
        from src.embeddings import EmbeddingEngine  # noqa: F401
        print("✓ Embeddings imported")
        from src.storage import MemoryStorage  # noqa: F401
        print("✓ Storage imported")
        from src.api import app  # noqa: F401

        print("✓ API imported")

        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_config():
    """Test configuration."""
    print("\nTesting configuration...")
    from src.config import settings

    if not os.path.exists(".env"):
        print("✗ .env file not found")
        return False

    print("✓ .env file exists")

    if settings.openrouter_api_key == "your_openrouter_api_key_here":
        print("✗ OpenRouter API key not configured")
        return False

    print("✓ OpenRouter API key configured")
    return True


def test_model():
    """Test if ONNX model exists."""
    print("\nTesting ONNX model...")
    from src.config import settings

    if not os.path.exists(settings.onnx_model_path):
        print(f"✗ ONNX model not found at {settings.onnx_model_path}")
        print("  Run: python scripts/download_model.py")
        return False

    print("✓ ONNX model found")
    return True


def test_embeddings():
    """Test embedding generation."""
    print("\nTesting embeddings...")
    try:
        from src.embeddings import EmbeddingEngine

        engine = EmbeddingEngine()

        # Test single text
        embedding = engine.encode("This is a test sentence.")
        assert embedding.shape == (1, 384), f"Wrong shape: {embedding.shape}"
        print("✓ Single text embedding works")

        # Test batch
        embeddings = engine.encode(["First text", "Second text"])
        assert embeddings.shape == (2, 384), f"Wrong shape: {embeddings.shape}"
        print("✓ Batch embedding works")

        return True
    except Exception as e:
        print(f"✗ Embedding error: {e}")
        return False


def test_storage():
    """Test storage initialization."""
    print("\nTesting storage...")
    try:
        from src.storage import MemoryStorage

        MemoryStorage()
        print("✓ Storage initialized")
        return True
    except Exception as e:
        print(f"✗ Storage error: {e}")
        print("  Make sure Qdrant is running: docker-compose up -d")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Smart-Meet Lite System Test")
    print("=" * 60)

    tests = [test_imports, test_config, test_model, test_embeddings, test_storage]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")

    if passed == len(tests):
        print("\n✓ All tests passed! System is ready.")
        print("\nStart the API with: python -m src.api")
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")


if __name__ == "__main__":
    main()
