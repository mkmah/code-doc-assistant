"""Secret detection and redaction utilities for code scanning."""

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class SecretDetection:
    """A single secret detection result."""

    file_path: str
    secret_type: str
    line: int
    column: int
    snippet: str
    secret_count: int


@dataclass
class SecretScanResult:
    """Result of scanning code for secrets."""

    file_path: str
    has_secrets: bool
    detections: list[SecretDetection]
    total_count: int


# Secret detection patterns with regex
SECRET_PATTERNS: ClassVar[dict[str, str]] = {
    "AWS_API_KEY": r"\bAKIA[0-9A-Z]{16,}\b",
    "GITHUB_TOKEN": r"\bghp_[a-zA-Z0-9]{36}\b",
    "GITHUB_OAUTH": r"\bgho_[a-zA-Z0-9]{36}\b",
    "GITHUB_APP": r"\b(ghu|ghs)_[a-zA-Z0-9]{36}\b",
    "JWT_TOKEN": r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
    "SLACK_TOKEN": r"\bxox[pbar]-[0-9]{12}-[0-9]{12}-[0-9]{12}-[a-z0-9]{32}",
    "BASIC_AUTH": r"://[^\s]+:[^\s]+@",
    "PASSWORD_ASSIGNMENT": r'password\s*[=:]\s*["\'][^"\']+["\']',
    "API_KEY_ASSIGNMENT": r'["\']?(api[_-]?key|token|secret|private[_-]?key)["\']?\s*[=:]\s*["\']([a-zA-Z0-9_\-]{16,})["\']',
    "PRIVATE_KEY_HEADER": r"-----BEGIN [A-Z]+ PRIVATE KEY-----",
    "BEARER_TOKEN": r'["\']?Bearer\s+["\']?([a-zA-Z0-9_\-\.]{20,})["\']',
    "HEROKU_API_KEY": r"[hH][eE][rR][oO][kK][uU]\s*-\s*[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}",
    "FIREBASE_TOKEN": r"\b[0-9]+/[0-9A-Za-z_-]{20,}",
    "STRIPE_KEY": r"\bsk_(live|test)_[0-9A-Za-z]{24,}\b",
    "SENDGRID_KEY": r"\bSG\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}\b",
    "TWILIO_KEY": r"\bSK[0-9a-fA-F]{32}\b",
    "MAILGUN_KEY": r"[a-zA-Z0-9_-]{32,}.*mailgun\.com",
    "DOCKER_AUTH": r"'[a-z0-9]{32,}'",
}


def scan_for_secrets(content: str, file_path: str) -> SecretScanResult:
    """Scan code content for potential secrets.

    Args:
        content: The file content to scan
        file_path: The file path being scanned (for reporting)

    Returns:
        SecretScanResult with detection details including line numbers
    """
    detections = []
    lines = content.split("\n")

    # Compile patterns for efficiency
    compiled_patterns = {
        secret_type: re.compile(pattern, re.IGNORECASE)
        for secret_type, pattern in SECRET_PATTERNS.items()
    }

    for line_num, line in enumerate(lines, start=1):
        for secret_type, pattern in compiled_patterns.items():
            matches = pattern.finditer(line)
            line_secret_count = 0

            for match in matches:
                # Get snippet (first 25 chars for readability)
                matched_text = match.group()
                snippet = matched_text[:25] + "..." if len(matched_text) > 25 else matched_text

                detection = SecretDetection(
                    file_path=file_path,
                    secret_type=secret_type,
                    line=line_num,
                    column=match.start() + 1,
                    snippet=snippet,
                    secret_count=1,
                )
                detections.append(detection)
                line_secret_count += 1

    return SecretScanResult(
        file_path=file_path,
        has_secrets=len(detections) > 0,
        detections=detections,
        total_count=len(detections),
    )


def redact_secrets(content: str, scan_result: SecretScanResult | None = None) -> tuple[str, SecretScanResult]:
    """Redact secrets from content by replacing with [REDACTED_TYPE] placeholders.

    Args:
        content: The file content to redact
        scan_result: Optional pre-computed scan result. If not provided, will scan first.

    Returns:
        Tuple of (redacted_content, scan_result) with replacements made
    """
    # If no scan result provided, scan first
    if scan_result is None:
        scan_result = scan_for_secrets(content, file_path="")

    lines = content.split("\n")
    redacted_lines = []

    # Compile patterns for redaction
    compiled_patterns = {
        secret_type: re.compile(pattern, re.IGNORECASE)
        for secret_type, pattern in SECRET_PATTERNS.items()
    }

    for line_num, line in enumerate(lines, start=1):
        redacted_line = line

        for secret_type, pattern in compiled_patterns.items():
            # Replace all matches of this pattern with placeholder
            placeholder = f"[REDACTED_{secret_type}]"
            redacted_line = pattern.sub(placeholder, redacted_line)

        redacted_lines.append(redacted_line)

    redacted_content = "\n".join(redacted_lines)

    return redacted_content, scan_result


def get_secret_summary(scan_results: list[SecretScanResult]) -> dict[str, dict[str, int]]:
    """Summarize secret detections across multiple files.

    Args:
        scan_results: List of scan results from multiple files

    Returns:
        Dictionary mapping file_path to detection counts by type
    """
    summary = {}

    for result in scan_results:
        if not result.has_secrets:
            continue

        file_summary: dict[str, int] = {}
        for detection in result.detections:
            secret_type = detection.secret_type
            file_summary[secret_type] = file_summary.get(secret_type, 0) + 1

        summary[result.file_path] = file_summary

    return summary
