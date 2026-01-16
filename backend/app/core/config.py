"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys
    anthropic_api_url: str = Field(default="https://api.anthropic.com", description="Anthropic API URL for Claude")
    anthropic_api_key: str = Field(..., description="Anthropic API key for Claude")
    anthropic_model: str = Field(default="claude-3-5-sonnet-20241022", description="Anthropic model for Claude")
    jina_api_key: str = Field(..., description="Jina AI API key for embeddings")

    # Backend
    backend_port: int = Field(default=8000, description="Backend server port")
    backend_host: str = Field(default="0.0.0.0", description="Backend server host")
    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", description="Logging level"
    )

    # ChromaDB
    chromadb_host: str = Field(default="chroma", description="ChromaDB host")
    chromadb_port: int = Field(default=8000, description="ChromaDB port")
    chromadb_token: str = Field(default="test-token", description="ChromaDB token")
    chromadb_collection: str = Field(default="code_chunks", description="ChromaDB collection")
    chromadb_persist_directory: str = Field(
        default="/chroma/chroma", description="ChromaDB persist directory"
    )

    # Temporal
    temporal_host: str = Field(default="temporal", description="Temporal server host")
    temporal_port: int = Field(default=7233, description="Temporal server port")

    # PostgreSQL (for Temporal)
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")
    postgres_db: str = Field(default="temporal", description="PostgreSQL database")

    # Application Database (PostgreSQL - separate from Temporal DB)
    app_db_name: str = Field(default="code_doc_assistant", description="Application database name")
    app_db_pool_size: int = Field(default=5, description="Database connection pool size")
    app_db_max_overflow: int = Field(default=10, description="Database max overflow")

    # Redis Configuration
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: str | None = Field(default=None, description="Redis password")
    redis_ttl_seconds: int = Field(default=604800, description="Redis key TTL (7 days default)")
    redis_pool_size: int = Field(default=10, description="Redis connection pool size")

    # File Upload
    max_file_size_bytes: int = Field(
        default=104857600, description="Maximum file size in bytes (100MB)"
    )

    # Performance
    embedding_batch_size: int = Field(
        default=10, description="Number of embeddings to generate per batch"
    )
    chunk_min_tokens: int = Field(default=512, description="Minimum chunk size in tokens")
    chunk_max_tokens: int = Field(default=1024, description="Maximum chunk size in tokens")
    chunk_overlap_tokens: int = Field(default=50, description="Overlap between chunks in tokens")
    default_top_k_results: int = Field(
        default=5, description="Default number of results to retrieve"
    )
    max_top_k_results: int = Field(default=20, description="Maximum number of results to retrieve")

    # Retry
    retry_initial_interval_seconds: int = Field(
        default=2, description="Initial retry interval in seconds"
    )
    retry_max_interval_seconds: int = Field(
        default=60, description="Maximum retry interval in seconds"
    )
    retry_max_elapsed_time_seconds: int = Field(
        default=1800, description="Maximum retry elapsed time in seconds (30 min)"
    )

    # Rate Limiting
    rate_limit_per_hour: int = Field(
        default=100, description="Rate limit: requests per hour per IP address"
    )
    rate_limit_concurrent_queries: int = Field(
        default=10, description="Rate limit: maximum concurrent query requests"
    )

    # Storage
    storage_path: str = Field(
        default="storage/codebases", description="Path for storing uploaded codebase files (relative to repo root)"
    )

    # Feature Flags
    enable_secret_detection: bool = Field(
        default=True, description="Enable secret detection and redaction"
    )
    enable_streaming: bool = Field(default=True, description="Enable streaming responses")
    session_timeout_seconds: int = Field(
        default=3600, description="Session timeout in seconds (1 hour)"
    )
    session_retention_days: int = Field(
        default=7, description="Session retention period in days"
    )

    # Tracing
    enable_tracing: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    tracing_endpoint: str | None = Field(
        default=None, description="OTLP endpoint for traces (e.g., http://jaeger:4317)"
    )

    environment: str = Field(default="dev", description="Environment")

    @field_validator("anthropic_api_key", "jina_api_key")
    @classmethod
    def validate_required_api_keys(cls, v: str, info) -> str:
        """Validate that required API keys are not empty."""
        if not v or v.startswith("your_"):
            raise ValueError(f"{info.field_name} must be set")
        return v

    @property
    def chromadb_url(self) -> str:
        """Construct ChromaDB URL from host and port."""
        return f"http://{self.chromadb_host}:{self.chromadb_port}"

    @property
    def temporal_url(self) -> str:
        """Construct Temporal URL from host and port."""
        return f"{self.temporal_host}:{self.temporal_port}"

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL URL from components."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def app_db_url(self) -> str:
        """Construct async PostgreSQL URL for application database."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.app_db_name}"
        )

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    This function caches the settings object to avoid re-parsing
    environment variables on every call.
    """
    return Settings()
