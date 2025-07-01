"""Setup script for Smart-Meet Lite."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.storage import MemoryStorage
from src.config import settings


def setup_database():
    """Initialize SQLite database and Qdrant collection."""
    print("Setting up Smart-Meet Lite...")

    # Create data directory
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    print(f"✓ Created data directory: {data_dir}")

    # Initialize storage (creates tables and collection)
    try:
        MemoryStorage()
        print(f"✓ Initialized SQLite database at: {settings.database_path}")
        print(f"✓ Initialized Qdrant collection: {settings.qdrant_collection}")
    except Exception as e:
        print(f"✗ Error initializing storage: {e}")
        print("\nMake sure Qdrant is running:")
        print("  docker-compose up -d")
        return False

    return True


def check_model():
    """Check if ONNX model exists."""
    model_path = Path(settings.onnx_model_path)
    if not model_path.exists():
        print(f"\n⚠ ONNX model not found at: {model_path}")
        print("Run: python scripts/download_model.py")
        return False
    print(f"✓ ONNX model found at: {model_path}")
    return True


def check_env():
    """Check environment configuration."""
    if not os.path.exists(".env"):
        print("\n⚠ .env file not found!")
        print("Copy .env.example to .env and configure:")
        print("  cp .env.example .env")
        print("  # Edit .env and add your OpenRouter API key")
        return False

    if (
        not settings.openrouter_api_key
        or settings.openrouter_api_key == "your_openrouter_api_key_here"
    ):
        print("\n⚠ OpenRouter API key not configured!")
        print("Edit .env and add your OpenRouter API key")
        return False

    print("✓ Environment configured")
    return True


def main():
    """Run complete setup."""
    print("=" * 60)
    print("Smart-Meet Lite Setup")
    print("=" * 60)

    # Check environment
    if not check_env():
        sys.exit(1)

    # Setup database
    if not setup_database():
        sys.exit(1)

    # Check model
    if not check_model():
        print("\nSetup incomplete. Please download the model.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✓ Setup complete!")
    print("\nNext steps:")
    print("1. Make sure Qdrant is running: docker-compose up -d")
    print("2. Start the API: python -m src.api")
    print("3. Access the API at: http://localhost:8000")
    print("4. API docs at: http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    main()
