"""Unit tests for secret detection utilities."""

import pytest

from app.utils.secret_detection import (
    SECRET_PATTERNS,
    get_secret_summary,
    redact_secrets,
    scan_for_secrets,
)


class TestScanForSecrets:
    """Tests for scan_for_secrets function."""

    def test_scan_aws_api_key(self):
        """Test detection of AWS API keys."""
        code = "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF"
        result = scan_for_secrets(code, "test.py")

        assert result.has_secrets is True
        assert result.total_count == 1
        assert len(result.detections) == 1
        assert result.detections[0].secret_type == "AWS_API_KEY"
        assert result.detections[0].line == 1
        assert "AKIA1234567890ABCDEF" in result.detections[0].snippet

    def test_scan_github_token(self):
        """Test detection of GitHub personal access tokens."""
        code = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        result = scan_for_secrets(code, "config.sh")

        assert result.has_secrets is True
        assert result.total_count >= 1
        assert any(d.secret_type == "GITHUB_TOKEN" for d in result.detections)

    def test_scan_jwt_token(self):
        """Test detection of JWT tokens."""
        code = 'const token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnopqrstuvwxyz";'
        result = scan_for_secrets(code, "auth.js")

        assert result.has_secrets is True
        assert any(d.secret_type == "JWT_TOKEN" for d in result.detections)

    def test_scan_password_assignment(self):
        """Test detection of password in string assignments."""
        code = 'password = "super_secret_password123"'
        result = scan_for_secrets(code, "config.py")

        assert result.has_secrets is True
        assert any("PASSWORD" in d.secret_type for d in result.detections)

    def test_scan_private_key_header(self):
        """Test detection of private key headers."""
        code = "-----BEGIN RSA PRIVATE KEY-----"
        result = scan_for_secrets(code, "key.pem")

        assert result.has_secrets is True
        assert result.detections[0].secret_type == "PRIVATE_KEY_HEADER"

    def test_scan_bearer_token(self):
        """Test detection of Bearer tokens."""
        code = 'Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"'
        result = scan_for_secrets(code, "request.py")

        assert result.has_secrets is True
        # Should match either API_KEY_ASSIGNMENT or BEARER_TOKEN
        assert result.total_count >= 1

    def test_scan_clean_code(self):
        """Test that clean code returns no detections."""
        code = """
def hello_world():
    print("Hello, World!")
    return 42

x = 5
y = 10
"""
        result = scan_for_secrets(code, "clean.py")

        assert result.has_secrets is False
        assert result.total_count == 0
        assert len(result.detections) == 0

    def test_scan_multiple_secrets(self):
        """Test detection of multiple different secret types."""
        code = """
AWS_KEY=AKIA1234567890ABCDEF
GITHUB=ghp_1234567890abcdefghijklmnopqrstuvwxyz
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dothang"
"""
        result = scan_for_secrets(code, "config.py")

        assert result.has_secrets is True
        assert result.total_count >= 3
        assert len(result.detections) >= 3

    def test_scan_tracks_line_numbers(self):
        """Test that detections include correct line numbers."""
        code = """line 1
AKIA1234567890ABCDEF
line 3
line 4"""
        result = scan_for_secrets(code, "test.py")

        assert result.detections[0].line == 2

    def test_scan_tracks_column_position(self):
        """Test that detections include column positions."""
        code = "AKIA1234567890ABCDEF"
        result = scan_for_secrets(code, "test.py")

        assert result.detections[0].column == 1


class TestRedactSecrets:
    """Tests for redact_secrets function."""

    def test_redact_aws_api_key(self):
        """Test redaction of AWS API keys."""
        code = "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF"
        redacted, result = redact_secrets(code)

        assert "[REDACTED_AWS_API_KEY]" in redacted
        assert "AKIA1234567890ABCDEF" not in redacted
        assert result.has_secrets is True

    def test_redact_jwt_token(self):
        """Test redaction of JWT tokens."""
        code = 'token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123def456"'
        redacted, result = redact_secrets(code)

        assert "[REDACTED_JWT_TOKEN]" in redacted
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted

    def test_redact_multiple_secrets(self):
        """Test redaction of multiple secrets in one file."""
        code = """AWS_KEY=AKIA1234567890ABCDEF
GITHUB=ghp_1234567890abcdefghijklmnopqrstuvwxyz
"""
        redacted, result = redact_secrets(code)

        assert "[REDACTED_AWS_API_KEY]" in redacted
        assert "[REDACTED_GITHUB_TOKEN]" in redacted
        assert "AKIA1234567890ABCDEF" not in redacted
        assert "ghp_" not in redacted

    def test_redact_preserves_code_structure(self):
        """Test that redaction preserves code structure."""
        code = """def get_api_key():
    return "AKIA1234567890ABCDEF"
"""
        redacted, result = redact_secrets(code)

        assert "def get_api_key():" in redacted
        assert "return " in redacted
        assert "[REDACTED_AWS_API_KEY]" in redacted

    def test_redact_with_precomputed_scan_result(self):
        """Test redaction using pre-computed scan result."""
        code = "AKIA1234567890ABCDEF"
        scan_result = scan_for_secrets(code, "test.py")
        redacted, returned_result = redact_secrets(code, scan_result)

        assert returned_result is scan_result
        assert "[REDACTED_AWS_API_KEY]" in redacted


class TestGetSecretSummary:
    """Tests for get_secret_summary function."""

    def test_summarize_single_file(self):
        """Test summarizing secrets in a single file."""
        scan_results = [
            scan_for_secrets("AKIA1234567890ABCDEF", "test.py"),
        ]
        summary = get_secret_summary(scan_results)

        assert "test.py" in summary
        assert summary["test.py"]["AWS_API_KEY"] == 1

    def test_summarize_multiple_files(self):
        """Test summarizing secrets across multiple files."""
        scan_results = [
            scan_for_secrets("AKIA1234567890ABCDEF", "config.py"),
            scan_for_secrets("AKIA9999999999999999", "secrets.py"),
            scan_for_secrets("ghp_1234567890abcdefghijklmnopqrstuvwxyz", "config.sh"),
        ]
        summary = get_secret_summary(scan_results)

        assert len(summary) == 3
        assert "config.py" in summary
        assert "secrets.py" in summary
        assert "config.sh" in summary

    def test_summarize_empty_results(self):
        """Test summarizing when no secrets found."""
        clean_code = "def hello():\n    return 'world'"
        scan_results = [
            scan_for_secrets(clean_code, "clean.py"),
        ]
        summary = get_secret_summary(scan_results)

        assert len(summary) == 0

    def test_summarize_counts_by_type(self):
        """Test that summary counts secrets by type."""
        code = """AKIA1111111111111111
AKIA2222222222222222
ghp_1234567890abcdefghijklmnopqrstuvwxyz"""
        scan_results = [scan_for_secrets(code, "config.py")]
        summary = get_secret_summary(scan_results)

        assert summary["config.py"]["AWS_API_KEY"] == 2
        assert summary["config.py"]["GITHUB_TOKEN"] == 1


class TestSecretPatterns:
    """Tests for secret detection patterns."""

    def test_all_patterns_are_valid_regex(self):
        """Test that all defined patterns compile successfully."""
        import re

        for name, pattern in SECRET_PATTERNS.items():
            # Should not raise exception
            compiled = re.compile(pattern, re.IGNORECASE)
            assert compiled is not None

    def test_heroku_api_key_pattern(self):
        """Test Heroku API key pattern."""
        code = "HEROKU_API_KEY=heroku-01234567-89ab-cdef-0123-456789abcdef"
        result = scan_for_secrets(code, "config.py")

        assert result.has_secrets is True
        assert any("HEROKU" in d.secret_type for d in result.detections)

    def test_firebase_token_pattern(self):
        """Test Firebase token pattern."""
        code = "firebase_token='1/03abcdefghijklmnopqrstuvwxyz12345'"
        result = scan_for_secrets(code, "firebase.py")

        assert result.has_secrets is True

    def test_stripe_key_pattern(self):
        """Test Stripe API key pattern."""
        code = "stripe_key='sk_test_51AbCdEf1234567890abcdefghij'"
        result = scan_for_secrets(code, "payment.py")

        assert result.has_secrets is True
        assert any("STRIPE" in d.secret_type for d in result.detections)

    def test_sendgrid_key_pattern(self):
        """Test SendGrid API key pattern."""
        code = "SENDGRID_API_KEY='SG.abcdefghijklmnopqrstuvwxyz12345.abcdefghijklmnopqrstuvwxyz12345'"
        result = scan_for_secrets(code, "email.py")

        assert result.has_secrets is True
        assert any("SENDGRID" in d.secret_type for d in result.detections)

    def test_twilio_key_pattern(self):
        """Test Twilio API key pattern."""
        code = "TWILIO_ACCOUNT_SID='test1234567890abcdef1234567890abcdef'"
        result = scan_for_secrets(code, "sms.py")

        assert result.has_secrets is True
        assert any("TWILIO" in d.secret_type for d in result.detections)
