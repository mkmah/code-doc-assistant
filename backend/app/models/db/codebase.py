"""Codebase SQLAlchemy model."""

from enum import Enum as PyEnum

from sqlalchemy import JSON, BigInteger, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db.base import Base, TimestampMixin, UUIDMixin


class SourceType(PyEnum):
    """Codebase source type enumeration."""

    ZIP = "zip"
    GITHUB_URL = "github_url"


class CodebaseStatus(PyEnum):
    """Codebase processing status enumeration."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Codebase(Base, UUIDMixin, TimestampMixin):
    """SQLAlchemy model for codebase metadata."""

    __tablename__ = "codebases"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Source info
    source_type: Mapped[SourceType] = mapped_column(
        Enum(
            SourceType,
            name="source_type",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Status
    status: Mapped[CodebaseStatus] = mapped_column(
        Enum(
            CodebaseStatus,
            name="codebase_status",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=CodebaseStatus.QUEUED,
        nullable=False,
        index=True,
    )

    # File processing stats
    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Language info
    primary_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    all_languages: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Size info
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Workflow tracking
    workflow_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    # Security
    secrets_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # File storage path (still using local filesystem)
    storage_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
