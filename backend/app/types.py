from dataclasses import dataclass, field
from uuid import UUID


@dataclass
class IngestionInput:
    """Input for the ingestion workflow."""

    codebase_id: UUID
    source_type: str  # "zip" or "github_url"
    source_url: str | None = None
    file_data: bytes | None = None


@dataclass
class IngestionResult:
    """Result of the ingestion workflow."""

    status: str
    chunks_created: int
    files_processed: int
    secrets_found: int
    secrets_summary: dict[str, dict[str, int]] = field(default_factory=dict)
    error: str | None = None


@dataclass
class IngestionStatus:
    """Status signal for ingestion progress."""

    codebase_id: UUID
    step: str  # "validating", "cloning", "parsing", "embedding", "indexing", "completed", "failed"
    progress: float  # 0.0 to 1.0
    files_processed: int
    files_total: int
    chunks_created: int
    secrets_found: int
    secrets_summary: dict[str, dict[str, int]] = field(default_factory=dict)
    message: str = ""
    error: str | None = None


@dataclass
class SessionCleanupInput:
    """Input for the session cleanup workflow.

    For cron workflows, this can be empty as the workflow
    runs on a schedule without input.
    """

    pass


@dataclass
class SessionCleanupResult:
    """Result of the session cleanup workflow."""

    status: str
    cleaned_sessions: int
    retention_days: int
    error: str | None = None
