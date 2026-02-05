"""Tests for the mbox converter module."""

import tempfile
import os
from pathlib import Path

import pytest

from mac_mail_backup.converter import MboxConverter


class TestMboxConverter:
    """Test suite for MboxConverter class."""

    def test_init(self):
        """Test converter initialization."""
        converter = MboxConverter()
        assert converter.verbose is False

        converter_verbose = MboxConverter(verbose=True)
        assert converter_verbose.verbose is True

    def test_parse_emlx_valid(self, tmp_path):
        """Test parsing a valid emlx file."""
        # Create a mock emlx file
        email_content = b"From: test@example.com\r\nTo: recipient@example.com\r\nSubject: Test\r\n\r\nThis is the body."
        emlx_content = f"{len(email_content)}\n".encode() + email_content + b"\n<?xml version..."

        emlx_file = tmp_path / "test.emlx"
        emlx_file.write_bytes(emlx_content)

        converter = MboxConverter()
        result = converter.parse_emlx(str(emlx_file))

        assert result is not None
        assert b"From: test@example.com" in result
        assert b"This is the body." in result

    def test_parse_emlx_nonexistent(self):
        """Test parsing a non-existent file."""
        converter = MboxConverter()
        result = converter.parse_emlx("/nonexistent/path/file.emlx")
        assert result is None

    def test_get_from_line(self):
        """Test generating mbox From line."""
        converter = MboxConverter()

        email = b"From: sender@example.com\r\nDate: Mon, 01 Jan 2024 12:00:00 +0000\r\n\r\nBody"
        from_line = converter.get_from_line(email)

        assert from_line.startswith("From ")
        assert "sender@example.com" in from_line
        assert from_line.endswith("\n")

    def test_get_from_line_with_name(self):
        """Test From line extraction with display name."""
        converter = MboxConverter()

        email = b"From: John Doe <john@example.com>\r\n\r\nBody"
        from_line = converter.get_from_line(email)

        assert "john@example.com" in from_line

    def test_escape_from_lines(self):
        """Test escaping From lines in email body."""
        converter = MboxConverter()

        content = b"Line 1\nFrom someone@example.com\nLine 3"
        escaped = converter.escape_from_lines(content)

        assert b">From someone@example.com" in escaped
        # The "From " at the start of a line should be escaped to ">From "
        assert b"\nFrom " not in escaped

    def test_find_emlx_files(self, tmp_path):
        """Test finding emlx files recursively."""
        # Create directory structure with emlx files
        (tmp_path / "folder1").mkdir()
        (tmp_path / "folder1" / "test1.emlx").touch()
        (tmp_path / "folder1" / "test2.emlx").touch()
        (tmp_path / "folder2").mkdir()
        (tmp_path / "folder2" / "test3.partial.emlx").touch()
        (tmp_path / "other.txt").touch()

        converter = MboxConverter()
        files = converter.find_emlx_files(str(tmp_path))

        assert len(files) == 3
        assert all(f.endswith('.emlx') for f in files)

    def test_convert_folder_empty(self, tmp_path):
        """Test converting an empty folder."""
        source = tmp_path / "source"
        source.mkdir()

        output = tmp_path / "output.mbox"

        converter = MboxConverter()
        count = converter.convert_folder(str(source), str(output))

        assert count == 0
        assert not output.exists()


class TestFromLineGeneration:
    """Additional tests for From line generation edge cases."""

    def test_missing_from_header(self):
        """Test handling missing From header."""
        converter = MboxConverter()
        email = b"To: recipient@example.com\r\n\r\nBody"
        from_line = converter.get_from_line(email)

        assert "MAILER-DAEMON" in from_line

    def test_missing_date_header(self):
        """Test handling missing Date header."""
        converter = MboxConverter()
        email = b"From: sender@example.com\r\n\r\nBody"
        from_line = converter.get_from_line(email)

        # Should still generate a valid From line with current date
        assert from_line.startswith("From ")
        assert "sender@example.com" in from_line

    def test_malformed_email(self):
        """Test handling malformed email content."""
        converter = MboxConverter()
        email = b"This is not a valid email format"
        from_line = converter.get_from_line(email)

        # Should fall back to default values
        assert from_line.startswith("From ")
