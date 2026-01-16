"""Pydantic models for request/response schemas."""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class SourceType(str, Enum):
    """Codebase upload source type."""

    ZIP = "zip"
    GITHUB_URL = "github_url"


class CodebaseStatus(str, Enum):
    """Codebase ingestion status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkType(str, Enum):
    """Semantic code chunk type."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    IMPORT = "import"


class MessageType(str, Enum):
    """Chat message role."""

    USER = "user"
    ASSISTANT = "assistant"


class IngestionStep(str, Enum):
    """Current ingestion workflow step."""

    VALIDATING = "validating"
    CLONING = "cloning"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"
    COMPLETE = "complete"


class SecretType(str, Enum):
    """Types of secrets that can be detected."""

    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    GITHUB_TOKEN = "github_token"
    SLACK_TOKEN = "slack_token"
    PASSWORD = "password"
    PRIVATE_KEY = "private_key"


# =============================================================================
# Request Models
# =============================================================================


class UploadRequest(BaseModel):
    """Request model for codebase upload."""

    name: str = Field(..., min_length=1, max_length=100, description="Codebase name")
    description: str | None = Field(
        None, max_length=500, description="Optional codebase description"
    )
    repository_url: str | None = Field(
        None,
        pattern=r"^https://github\.com/[^/]+/[^/]+",
        description="GitHub repository URL",
    )


class ChatRequest(BaseModel):
    """Request model for chat query."""

    codebase_id: UUID = Field(..., description="Target codebase ID")
    query: str = Field(..., min_length=1, max_length=1000, description="User query")
    session_id: UUID | None = Field(None, description="Session ID for conversation context")
    stream: bool = Field(True, description="Whether to stream the response")


# =============================================================================
# Response Models
# =============================================================================


class UploadResponse(BaseModel):
    """Response model for successful upload."""

    codebase_id: UUID = Field(..., description="Generated codebase ID")
    status: Literal[CodebaseStatus.QUEUED, CodebaseStatus.PROCESSING] = Field(
        ..., description="Initial ingestion status"
    )
    workflow_id: str = Field(..., description="Temporal workflow ID for tracking")


class Source(BaseModel):
    """Code source citation."""

    file_path: str = Field(..., description="Source file path")
    line_start: int = Field(..., ge=1, description="Starting line number")
    line_end: int = Field(..., ge=1, description="Ending line number")
    snippet: str | None = Field(None, description="Code snippet preview")
    confidence: float | None = Field(None, ge=0, le=1, description="Relevance score")


class IngestionStatus(BaseModel):
    """Codebase ingestion status response."""

    codebase_id: UUID
    status: CodebaseStatus
    progress: float = Field(..., ge=0, le=100, description="Percentage complete")
    total_files: int = Field(..., ge=0, description="Total files to process")
    processed_files: int = Field(..., ge=0, description="Files successfully processed")
    current_step: IngestionStep | None = Field(None, description="Current workflow step")
    error: str | None = Field(None, description="Error message if failed")
    secrets_detected: list[dict] | None = Field(None, description="Secrets found during scanning")
    started_at: datetime | None = Field(None, description="Ingestion start time")
    completed_at: datetime | None = Field(None, description="Ingestion completion time")


class Codebase(BaseModel):
    """Codebase metadata."""

    id: UUID
    name: str
    description: str | None
    source_type: SourceType
    source_url: str | None
    status: CodebaseStatus
    total_files: int
    processed_files: int
    primary_language: str | None
    all_languages: list[str] | None
    size_bytes: int
    error_message: str | None
    workflow_id: str | None
    created_at: datetime
    updated_at: datetime
    secrets_detected: int = Field(default=0, ge=0, description="Count of secrets found during scanning")


class CodebaseListResponse(BaseModel):
    """Paginated list of codebases."""

    codebases: list[Codebase]
    total: int = Field(..., ge=0, description="Total number of codebases")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, le=100, description="Items per page")


# =============================================================================
# Internal Models
# =============================================================================


class CodeChunk(BaseModel):
    """Semantic code chunk for vector storage."""

    id: UUID
    codebase_id: UUID
    file_path: str
    line_start: int
    line_end: int
    content: str
    language: str
    chunk_type: ChunkType
    name: str | None = None  # Function/class name
    docstring: str | None = None
    dependencies: list[str] | None = None
    parent_class: str | None = None
    complexity: int | None = None
    embedding: list[float] | None = None
    metadata: dict = Field(default_factory=dict)


class SecretDetection(BaseModel):
    """Secret detection result."""

    file_path: str
    secret_count: int = Field(..., ge=0)


class QueryMessage(BaseModel):
    """Chat message."""

    message_id: UUID
    session_id: UUID
    role: MessageType
    content: str
    timestamp: datetime
    citations: list[Source] | None = None
    retrieved_chunks: list[UUID] | None = None
    token_count: int | None = None


class QuerySession(BaseModel):
    """Query session metadata."""

    session_id: UUID
    codebase_id: UUID
    created_at: datetime
    last_active: datetime
    message_count: int = Field(..., ge=0)
    context_chunks: list[UUID] | None = None


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""

    query: str
    response: str
    sources: list[Source] = Field(default_factory=list)
    timestamp: datetime


class Session(BaseModel):
    """Conversation session with history."""

    id: UUID
    codebase_id: UUID
    created_at: datetime
    last_access: datetime
    history: list[ConversationTurn] = Field(
        default_factory=list,
        max_length=20,
        description="Conversation history (max 20 turns for token budget)"
    )


class SecretDetectionResult(BaseModel):
    """Secret detection result from code scanning."""

    id: UUID
    codebase_id: UUID
    secret_type: SecretType
    file_path: str
    line_number: int = Field(..., ge=1, description="Line number where secret was found")
    redacted_placeholder: str = Field(
        ...,
        pattern=r"\[REDACTED_[A-Z_]+\]",
        description="Placeholder text replacing the secret"
    )
    detected_at: datetime


# =============================================================================
# Error Models
# =============================================================================


class ErrorDetail(BaseModel):
    """Error detail information."""

    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict | None = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: ErrorDetail
