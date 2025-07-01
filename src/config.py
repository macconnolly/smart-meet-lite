"""Configuration management using Pydantic Settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_path: str = "data/memories.db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "memories"

    # Model
    onnx_model_path: str = "models/onnx/all-MiniLM-L6-v2.onnx"

    # OpenRouter Configuration
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "google/gemini-2.5-flash-preview-05-20"

    # Memory Extraction
    min_memory_length: int = 30
    max_memory_length: int = 500

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
