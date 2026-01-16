"""Security utilities: secret detection, rate limiting, and concurrent query control."""

import asyncio
import re
from typing import ClassVar

from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SecretDetection(BaseModel):
    """A single secret detection result."""

    type: str = Field(..., description="Type of secret detected")
    line: int = Field(..., description="Line number where secret was detected")
    column: int = Field(..., description="Column number where secret was detected")
    snippet: str = Field(..., description="Snippet of the detected secret")
    replaced_with: str = Field(..., description="Replacement for the detected secret")


class SecretScanResult(BaseModel):
    """Result of scanning a file for secrets."""

    file_path: str = Field(..., description="Path to the file being scanned")
    has_secrets: bool = Field(..., description="Whether the file contains secrets")
    secret_count: int = Field(..., description="Number of secrets detected")
    detections: list[SecretDetection] = Field(
        ..., description="List of detected secrets"
    )


class SecretDetector:
    """Detects and redacts secrets in code."""

    # Secret detection patterns
    PATTERNS: ClassVar[dict[str, str]] = {
        "AWS_API_KEY": r"AKIA[0-9A-Z]{16}",
        "GITHUB_TOKEN": r"ghp_[a-zA-Z0-9]{36}",
        "JWT_TOKEN": r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
        "BASIC_AUTH": r"://[^:\s]+:[^@\s]+@",
        "PASSWORD_ASSIGNMENT": r'password\s*=\s*["\']([^"\']+)["\']',
        "API_KEY": r'["\']?(api[_-]?key|token|secret)["\']?\s*[:=]\s*["\']([a-zA-Z0-9_\-]{20,})["\']',
        "PRIVATE_KEY": r"-----BEGIN [A-Z]+ PRIVATE KEY-----",
        "BEARER_TOKEN": r'["\']?Bearer ["\']?([a-zA-Z0-9_\-\.]{20,})',
    }

    def __init__(self) -> None:
        """Initialize the secret detector with compiled regex patterns."""
        self._compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.PATTERNS.items()
        }

    def scan(self, content: str, file_path: str) -> SecretScanResult:
        """Scan content for potential secrets.

        Args:
            content: The file content to scan
            file_path: The file path being scanned

        Returns:
            SecretScanResult with detection details
        """
        detections = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for pattern_name, pattern in self._compiled_patterns.items():
                matches = pattern.finditer(line)
                for match in matches:
                    # Create placeholder string
                    placeholder = f"[REDACTED_{pattern_name}]"

                    # Get snippet (first 20 chars of match)
                    matched_text = match.group()
                    snippet = (
                        matched_text[:20] + "..."
                        if len(matched_text) > 20
                        else matched_text
                    )

                    detection = SecretDetection(
                        type=pattern_name,
                        line=line_num,
                        column=match.start() + 1,
                        snippet=snippet,
                        replaced_with=placeholder,
                    )
                    detections.append(detection)

        return SecretScanResult(
            file_path=file_path,
            has_secrets=len(detections) > 0,
            secret_count=len(detections),
            detections=detections,
        )

    def redact(self, content: str) -> tuple[str, SecretScanResult]:
        """Redact secrets from content.

        Args:
            content: The file content to redact

        Returns:
            Tuple of (redacted_content, scan_result)
        """
        detections = []
        lines = content.split("\n")
        redacted_lines = []

        for line_num, line in enumerate(lines, start=1):
            redacted_line = line
            line_detections = []

            for pattern_name, pattern in self._compiled_patterns.items():
                matches = pattern.finditer(line)
                for match in matches:
                    placeholder = f"[REDACTED_{pattern_name}]"
                    matched_text = match.group()
                    snippet = (
                        matched_text[:20] + "..."
                        if len(matched_text) > 20
                        else matched_text
                    )

                    detection = SecretDetection(
                        type=pattern_name,
                        line=line_num,
                        column=match.start() + 1,
                        snippet=snippet,
                        replaced_with=placeholder,
                    )
                    line_detections.append(detection)

                    # Replace with placeholder
                    redacted_line = redacted_line.replace(matched_text, placeholder)

            redacted_lines.append(redacted_line)
            detections.extend(line_detections)

        redacted_content = "\n".join(redacted_lines)

        scan_result = SecretScanResult(
            file_path="",
            has_secrets=len(detections) > 0,
            secret_count=len(detections),
            detections=detections,
        )

        return redacted_content, scan_result


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

# Global rate limiter instance (lazily initialized)
_limiter: Limiter | None = None


def get_limiter() -> Limiter:
    """Get or create the rate limiter instance.

    Lazy initialization ensures Redis connection is available first.

    Uses Token Bucket strategy which:
    - Allows short bursts for better user experience
    - Gradually refills tokens at a steady rate
    - Prevents sustained abuse while accommodating traffic spikes

    Returns:
        Configured Limiter instance with Redis storage and Token Bucket strategy
    """
    global _limiter
    if _limiter is None:
        # Create Redis storage backend for rate limiting
        # Using a synchronous redis connection (limits library requirement)
        # The key prefix ensures rate limit keys don't conflict with session data
        _limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=settings.redis_url,
            storage_options={"key_prefix": "limit:"},
            default_limits=[f"{settings.rate_limit_per_hour}/hour"],
            application_limits=[
                f"{settings.rate_limit_per_hour * 10}/hour"
            ],  # Global limit
        )

        logger.info(
            "rate_limiting_initialized",
            per_hour_limit=settings.rate_limit_per_hour,
            concurrent_limit=settings.rate_limit_concurrent_queries,
            storage="redis",
            strategy="token_bucket",
            storage_uri=settings.redis_url,
            key_prefix="limit:",
        )

    return _limiter


# Backwards compatibility: expose limiter as get_limiter()
# This allows existing code to use @limiter.limit() decorator
limiter = get_limiter()


# =============================================================================
# Concurrent Query Limiter
# =============================================================================


class ConcurrentQueryLimiter:
    """Limit concurrent query requests to prevent resource exhaustion.

    This prevents too many simultaneous LLM queries from overwhelming
    the system and causing timeouts or degraded performance.
    """

    def __init__(self, max_concurrent: int = 10):
        """Initialize the concurrent query limiter.

        Args:
            max_concurrent: Maximum number of concurrent queries allowed
        """
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._max_concurrent = max_concurrent
        self._active_count = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Attempt to acquire a query slot.

        Returns:
            True if slot acquired, False if at capacity
        """
        acquired = await self._semaphore.acquire()

        if acquired:
            async with self._lock:
                self._active_count += 1
                logger.debug(
                    "query_slot_acquired",
                    active_count=self._active_count,
                    max_concurrent=self._max_concurrent,
                )

        return acquired

    async def release(self) -> None:
        """Release a query slot."""
        async with self._lock:
            self._active_count -= 1
            logger.debug(
                "query_slot_released",
                active_count=self._active_count,
                max_concurrent=self._max_concurrent,
            )

        self._semaphore.release()

    @property
    def active_count(self) -> int:
        """Get current number of active queries."""
        return self._active_count

    @property
    def available_slots(self) -> int:
        """Get number of available query slots."""
        return self._max_concurrent - self._active_count

    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.release()


# Global concurrent query limiter instance
_concurrent_query_limiter: ConcurrentQueryLimiter | None = None


def get_concurrent_query_limiter() -> ConcurrentQueryLimiter:
    """Get the singleton concurrent query limiter instance."""
    global _concurrent_query_limiter
    if _concurrent_query_limiter is None:
        _concurrent_query_limiter = ConcurrentQueryLimiter(
            max_concurrent=settings.rate_limit_concurrent_queries
        )
        logger.info(
            "concurrent_query_limiter_created",
            max_concurrent=settings.rate_limit_concurrent_queries,
        )
    return _concurrent_query_limiter
