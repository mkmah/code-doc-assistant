"""Secret detection and redaction utilities."""

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class SecretDetection:
    """A single secret detection result."""

    type: str
    line: int
    column: int
    snippet: str
    replaced_with: str


@dataclass
class SecretScanResult:
    """Result of scanning a file for secrets."""

    file_path: str
    has_secrets: bool
    secret_count: int
    detections: list[SecretDetection]


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
                    snippet = matched_text[:20] + "..." if len(matched_text) > 20 else matched_text

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
                    snippet = matched_text[:20] + "..." if len(matched_text) > 20 else matched_text

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
