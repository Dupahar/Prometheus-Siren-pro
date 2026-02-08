# src/core/config.py
"""
Configuration management for Prometheus-Siren.
Loads settings from environment variables with validation.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # --- Gemini API ---
    gemini_api_key: str = Field(..., description="Google Gemini API key")
    
    # --- Qdrant Configuration ---
    qdrant_url: str = Field(..., description="Qdrant server URL")
    qdrant_api_key: str = Field(default="", description="Qdrant API key (optional for local)")
    
    # --- Collection Names ---
    qdrant_code_collection: str = Field(default="code_base", description="Collection for code embeddings")
    qdrant_attack_collection: str = Field(default="attack_memory", description="Collection for attack patterns")
    
    # --- Embedding Configuration ---
    embedding_model: str = Field(default="text-embedding-004", description="Gemini embedding model")
    embedding_dimension: int = Field(default=768, description="Embedding vector dimension")
    
<<<<<<< HEAD
=======
    # --- Gemini 3 Advanced Features ---
    thinking_level: str = Field(default="high", description="Gemini 2.0 Thinking Level (low/high)")
    context_cache_ttl: int = Field(default=300, description="Context Cache TTL in seconds")
    research_agent_enabled: bool = Field(default=True, description="Enable Deep Research Agent")
    
>>>>>>> fresh_submission
    # --- Prometheus Configuration ---
    prometheus_log_path: str = Field(default="./logs/app.log", description="Path to application logs")
    prometheus_approval_required: bool = Field(default=True, description="Require human approval for patches")
    
    # --- Siren Configuration ---
    siren_sandbox_timeout: int = Field(default=300, description="Sandbox session timeout in seconds")
    siren_max_sessions: int = Field(default=10, description="Maximum concurrent sandbox sessions")
    
    # --- Gateway Configuration ---
    gateway_host: str = Field(default="0.0.0.0", description="Gateway bind host")
    gateway_port: int = Field(default=8080, description="Gateway bind port")
    threat_threshold: float = Field(default=0.85, description="Similarity threshold for threat detection")
    
    @property
    def qdrant_has_api_key(self) -> bool:
        """Check if Qdrant API key is configured."""
        return bool(self.qdrant_api_key)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Singleton instance for easy import
settings = get_settings()
