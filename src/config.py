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
    qdrant_entity_collection: str = "entity_embeddings"

    # Model
    onnx_model_path: str = "models/onnx/all-MiniLM-L6-v2.onnx"

    # OpenRouter Configuration
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/o4-mini-high"  # Default model for OpenRouter

    # Memory Extraction
    min_memory_length: int = 30
    max_memory_length: int = 500
    
    # Query Engine
    timeline_display_limit: int = 10  # Number of timeline events to show in query results
    
    # Entity Resolution
    entity_resolution_threshold: float = 0.6  # Lower than current 80%
    create_deliverables_on_assignment: bool = True  # Auto-create task entities
    entity_resolution_use_llm: bool = True  # Enable LLM fallback

    # Proxy Configuration (for corporate environments)
    http_proxy: str = ""
    https_proxy: str = ""
    no_proxy: str = ""
    ssl_verify: bool = false  # Set to False to disable SSL verification

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
