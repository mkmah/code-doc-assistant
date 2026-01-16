"""Unit tests for secret scanner service.

This module tests the SecretScanner service which provides secret detection
for codebases during the ingestion process.

Tests follow TDD approach - written before implementation.
"""

import pytest
from uuid import uuid4

from app.models.schemas import SecretType


class TestSecretScannerService:
    """Tests for SecretScanner service functionality."""

    @pytest.fixture
    def scanner(self):
        """Create a SecretScanner instance for testing.

        Note: This will fail until T015 (implementation) is complete.
        """
        from app.services.secret_scanner import SecretScanner
        return SecretScanner()

    # ==========================================================================
    # AWS Credentials Tests
    # ==========================================================================

    def test_detect_aws_access_key(self, scanner):
        """Test detection of AWS access key ID."""
        code = "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF"
        results = scanner.scan_code(code, "test.py")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.AWS_ACCESS_KEY for r in results)

    def test_detect_aws_secret_key(self, scanner):
        """Test detection of AWS secret access key."""
        code = "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        results = scanner.scan_code(code, "config.py")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.AWS_SECRET_KEY for r in results)

    # ==========================================================================
    # API Keys Tests
    # ==========================================================================

    def test_detect_generic_api_key(self, scanner):
        """Test detection of generic API keys."""
        code = 'api_key = "sk-1234567890abcdefghijklmnopqrstuvwxyz12345678"'
        results = scanner.scan_code(code, "service.py")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.API_KEY for r in results)

    def test_detect_bearer_token(self, scanner):
        """Test detection of Bearer tokens."""
        code = 'Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"'
        results = scanner.scan_code(code, "auth.py")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.BEARER_TOKEN for r in results)

    # ==========================================================================
    # Service Tokens Tests
    # ==========================================================================

    def test_detect_github_token(self, scanner):
        """Test detection of GitHub personal access tokens."""
        code = "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        results = scanner.scan_code(code, ".env")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.GITHUB_TOKEN for r in results)

    def test_detect_slack_token(self, scanner):
        """Test detection of Slack tokens."""
        code = 'SLACK_TOKEN="xoxb-test-1234567890-1234567890123-ABCDEFGHIJ"'
        results = scanner.scan_code(code, "config.py")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.SLACK_TOKEN for r in results)

    # ==========================================================================
    # Password Tests
    # ==========================================================================

    def test_detect_password(self, scanner):
        """Test detection of password assignments."""
        code = 'database_password = "super_secret_password_123"'
        results = scanner.scan_code(code, "config.py")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.PASSWORD for r in results)

    # ==========================================================================
    # Private Keys Tests
    # ==========================================================================

    def test_detect_private_key(self, scanner):
        """Test detection of private key headers."""
        code = "-----BEGIN RSA PRIVATE KEY-----"
        results = scanner.scan_code(code, "key.pem")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.PRIVATE_KEY for r in results)

    def test_detect_ec_private_key(self, scanner):
        """Test detection of EC private keys."""
        code = "-----BEGIN EC PRIVATE KEY-----"
        results = scanner.scan_code(code, "ec_key.pem")

        assert len(results) > 0
        assert any(r.secret_type == SecretType.PRIVATE_KEY for r in results)

    # ==========================================================================
    # Multiple Secrets Tests
    # ==========================================================================

    def test_detect_multiple_secrets_in_file(self, scanner):
        """Test detection of multiple different secrets in one file."""
        code = """
AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF
GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
password = "my_secret_password_123"
"""
        results = scanner.scan_code(code, "config.py")

        # Should detect at least 3 secrets
        assert len(results) >= 3

        # Check for different types
        secret_types = {r.secret_type for r in results}
        assert SecretType.AWS_ACCESS_KEY in secret_types
        assert SecretType.GITHUB_TOKEN in secret_types
        assert SecretType.PASSWORD in secret_types

    def test_detect_secrets_across_multiple_lines(self, scanner):
        """Test detection of secrets on multiple lines."""
        code = """line 1
line 2 with AKIA1234567890ABCDEF
line 3
line 4 with ghp_1234567890abcdefghijklmnopqrstuvwxyz
line 5"""
        results = scanner.scan_code(code, "test.py")

        assert len(results) >= 2
        line_numbers = {r.line_number for r in results}
        assert 2 in line_numbers
        assert 4 in line_numbers

    # ==========================================================================
    # Clean Code Tests
    # ==========================================================================

    def test_no_false_positives_in_clean_code(self, scanner):
        """Test that clean code produces no false positives."""
        code = """
def hello_world():
    name = "World"
    print(f"Hello, {name}!")
    return 42

class Calculator:
    def add(self, a, b):
        return a + b
"""
        results = scanner.scan_code(code, "clean.py")

        assert len(results) == 0

    def test_common_non_secret_strings(self, scanner):
        """Test that common non-secret strings don't trigger detection."""
        code = """
api_endpoint = "https://api.example.com/v1"
max_retries = 3
timeout_seconds = 30
"""
        results = scanner.scan_code(code, "config.py")

        assert len(results) == 0

    # ==========================================================================
    # Metadata Tests
    # ==========================================================================

    def test_result_includes_file_path(self, scanner):
        """Test that scan results include the file path."""
        code = "AKIA1234567890ABCDEF"
        file_path = "config/secrets.py"
        results = scanner.scan_code(code, file_path)

        assert len(results) > 0
        assert all(r.file_path == file_path for r in results)

    def test_result_includes_line_number(self, scanner):
        """Test that scan results include correct line numbers."""
        code = """line 1
line 2 with AKIA1234567890ABCDEF
line 3"""
        results = scanner.scan_code(code, "test.py")

        assert results[0].line_number == 2

    def test_result_includes_redacted_placeholder(self, scanner):
        """Test that scan results include redaction placeholders."""
        code = "AKIA1234567890ABCDEF"
        results = scanner.scan_code(code, "test.py")

        assert len(results) > 0
        assert results[0].redacted_placeholder.startswith("[REDACTED_")
        assert results[0].redacted_placeholder.endswith("]")

    # ==========================================================================
    # Edge Cases Tests
    # ==========================================================================

    def test_empty_code(self, scanner):
        """Test scanning empty code."""
        results = scanner.scan_code("", "empty.py")

        assert len(results) == 0

    def test_code_with_only_whitespace(self, scanner):
        """Test scanning code with only whitespace."""
        code = "   \n\n\t\n   "
        results = scanner.scan_code(code, "whitespace.py")

        assert len(results) == 0

    def test_case_insensitive_detection(self, scanner):
        """Test that detection is case-insensitive."""
        code_lowercase = "aws_access_key_id=AKIA1234567890ABCDEF"
        code_uppercase = "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF"
        code_mixed = "AwS_AcCeSs_KeY_Id=AKIA1234567890ABCDEF"

        results_lower = scanner.scan_code(code_lowercase, "test.py")
        results_upper = scanner.scan_code(code_uppercase, "test.py")
        results_mixed = scanner.scan_code(code_mixed, "test.py")

        # All should detect the AWS key
        assert len(results_lower) > 0
        assert len(results_upper) > 0
        assert len(results_mixed) > 0


class TestSecretScannerServiceIntegration:
    """Integration tests for SecretScanner with codebase scanning."""

    @pytest.fixture
    def scanner(self):
        """Create a SecretScanner instance."""
        from app.services.secret_scanner import SecretScanner
        return SecretScanner()

    def test_scan_codebase_files(self, scanner):
        """Test scanning multiple files in a codebase."""
        files = {
            "config.py": "AWS_ACCESS_KEY_ID=AKIA1234567890ABCDEF",
            "auth.py": "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            "clean.py": "def hello(): pass"
        }

        results = []
        for file_path, content in files.items():
            file_results = scanner.scan_code(content, file_path)
            results.extend(file_results)

        # Should detect secrets in config.py and auth.py, but not clean.py
        assert len(results) >= 2

        # Check that secrets come from the right files
        secret_files = {r.file_path for r in results}
        assert "config.py" in secret_files
        assert "auth.py" in secret_files
        assert "clean.py" not in secret_files

    def test_get_secret_summary(self, scanner):
        """Test getting summary of detected secrets."""
        files = {
            "config.py": "AKIA1111111111111111\nAKIA2222222222222222",
            "secrets.py": "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        }

        all_results = []
        for file_path, content in files.items():
            file_results = scanner.scan_code(content, file_path)
            all_results.extend(file_results)

        summary = scanner.get_summary(all_results)

        # Verify summary counts
        assert "config.py" in summary
        assert "secrets.py" in summary
        assert summary["config.py"]["total_count"] >= 2
        assert summary["secrets.py"]["total_count"] >= 1
