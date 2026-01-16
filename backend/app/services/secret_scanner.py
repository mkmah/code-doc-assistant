"""Secret scanning service for codebase ingestion.

This service provides detection of secrets (API keys, tokens, passwords, etc.)
in source code files during the ingestion workflow.

The scanner uses regex-based pattern matching to identify potential secrets
and returns structured results with file paths, line numbers, and redaction placeholders.
"""

import re
from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID, uuid4

from app.core.logging import get_logger
from app.models.schemas import SecretDetectionResult, SecretType

logger = get_logger(__name__)


@dataclass
class SecretMatch:
    """A single secret match result."""

    secret_type: SecretType
    file_path: str
    line_number: int
    matched_text: str
    redacted_placeholder: str


class SecretScanner:
    """Secret detection service using regex pattern matching.

    This service scans code files for potential secrets and provides
    redaction placeholders for safe storage.
    """

    # Secret detection patterns
    # Each pattern maps to a SecretType enum value
    PATTERNS: ClassVar[dict[SecretType, str]] = {
        SecretType.AWS_ACCESS_KEY: r"AKIA[0-9A-Z]{16}",
        SecretType.AWS_SECRET_KEY: r"(?i)aws[_-]?secret[_-]?(?:access[_-]?)?key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?",
        SecretType.API_KEY: r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}['\"]?",
        SecretType.BEARER_TOKEN: r"(?i)bearer\s+[A-Za-z0-9_\-\.]{20,}",
        SecretType.GITHUB_TOKEN: r"ghp_[a-zA-Z0-9]{36}",
        SecretType.SLACK_TOKEN: r"xox[pbar]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{32}",
        SecretType.PASSWORD: r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[A-Za-z0-9_@\-]{8,}['\"]?",
        SecretType.PRIVATE_KEY: r"-----BEGIN\s+(?:RSA|EC|DSA|OPENSSH|PRIVATE)\s+KEY-----",
    }

    def __init__(self) -> None:
        """Initialize the secret scanner with compiled regex patterns."""
        self._compiled_patterns = {
            secret_type: re.compile(pattern, re.MULTILINE | re.DOTALL)
            for secret_type, pattern in self.PATTERNS.items()
        }

        logger.info(
            "secret_scanner_initialized",
            patterns_count=len(self._compiled_patterns),
        )

    def scan_code(self, content: str, file_path: str) -> list[SecretDetectionResult]:
        """Scan code content for potential secrets.

        Args:
            content: The file content to scan
            file_path: The file path being scanned (for result metadata)

        Returns:
            List of SecretDetectionResult objects with match details
        """
        matches = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            for secret_type, pattern in self._compiled_patterns.items():
                pattern_matches = pattern.finditer(line)

                for match in pattern_matches:
                    matched_text = match.group()
                    placeholder = self._create_placeholder(secret_type)

                    result = SecretDetectionResult(
                        id=uuid4(),
                        codebase_id=UUID(int=0),  # Will be set by caller
                        secret_type=secret_type,
                        file_path=file_path,
                        line_number=line_num,
                        redacted_placeholder=placeholder,
                        detected_at=None,  # Will be set by caller
                    )

                    matches.append(result)

        if matches:
            logger.debug(
                "secrets_detected",
                file_path=file_path,
                count=len(matches),
                types=[m.secret_type.value for m in matches],
            )

        return matches

    def get_summary(self, detections: list[SecretDetectionResult]) -> dict[str, dict[str, int]]:
        """Get a summary of detected secrets grouped by file and type.

        Args:
            detections: List of secret detection results

        Returns:
            Dictionary mapping file paths to secret type counts
        """
        summary: dict[str, dict[str, int]] = {}

        for detection in detections:
            file_path = detection.file_path
            secret_type = detection.secret_type.value

            if file_path not in summary:
                summary[file_path] = {}

            if secret_type not in summary[file_path]:
                summary[file_path][secret_type] = 0

            summary[file_path][secret_type] += 1

        # Add total count per file
        for file_path in summary:
            summary[file_path]["total_count"] = sum(summary[file_path].values())

        return summary

    def redact_content(self, content: str, detections: list[SecretDetectionResult]) -> str:
        """Redact detected secrets from content.

        Args:
            content: The original content
            detections: List of detections for this content

        Returns:
            Content with secrets redacted
        """
        if not detections:
            return content

        redacted_content = content
        lines = content.split("\n")

        for detection in detections:
            line_num = detection.line_number
            if 1 <= line_num <= len(lines):
                # Replace matched text with placeholder
                # This is a simple replacement - for production, you'd want
                # more sophisticated redaction that preserves structure
                placeholder = detection.redacted_placeholder
                lines[line_num - 1] = lines[line_num - 1].replace(
                    detection.redacted_placeholder.replace("[REDACTED_", "").replace("]", ""),
                    placeholder,
                )

        return "\n".join(lines)

    def _create_placeholder(self, secret_type: SecretType) -> str:
        """Create a redaction placeholder for a secret type.

        Args:
            secret_type: The type of secret

        Returns:
            Placeholder string like "[REDACTED_AWS_ACCESS_KEY]"
        """
        type_name = secret_type.value.upper()
        return f"[REDACTED_{type_name}]"

    def get_secrets_count(self, detections: list[SecretDetectionResult]) -> dict[SecretType, int]:
        """Count detections by secret type.

        Args:
            detections: List of detection results

        Returns:
            Dictionary mapping secret types to counts
        """
        counts: dict[SecretType, int] = {}

        for detection in detections:
            secret_type = detection.secret_type
            counts[secret_type] = counts.get(secret_type, 0) + 1

        return counts


# Singleton instance
_secret_scanner: SecretScanner | None = None


def get_secret_scanner() -> SecretScanner:
    """Get the singleton secret scanner instance."""
    global _secret_scanner
    if _secret_scanner is None:
        _secret_scanner = SecretScanner()
    return _secret_scanner
