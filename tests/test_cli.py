"""Tests for the CLI module."""

import pytest

from mac_mail_backup.cli import parse_args


class TestParseArgs:
    """Test suite for argument parsing."""

    def test_no_args(self):
        """Test with no arguments."""
        args = parse_args([])
        assert args.output_dir is None
        assert args.list is False
        assert args.account is None
        assert args.all is False
        assert args.quiet is False

    def test_output_dir_positional(self):
        """Test output directory as positional argument."""
        args = parse_args(["/path/to/backup"])
        assert args.output_dir == "/path/to/backup"

    def test_output_dir_flag(self):
        """Test output directory with -o flag."""
        args = parse_args(["-o", "/path/to/backup"])
        assert args.output_dir_flag == "/path/to/backup"

    def test_list_short(self):
        """Test --list short form."""
        args = parse_args(["-l"])
        assert args.list is True

    def test_list_long(self):
        """Test --list long form."""
        args = parse_args(["--list"])
        assert args.list is True

    def test_account_single(self):
        """Test single account selection."""
        args = parse_args(["-a", "1"])
        assert args.account == "1"

    def test_account_multiple(self):
        """Test multiple account selection."""
        args = parse_args(["-a", "1,2,3"])
        assert args.account == "1,2,3"

    def test_all_flag(self):
        """Test --all flag."""
        args = parse_args(["--all"])
        assert args.all is True

    def test_quiet_flag(self):
        """Test --quiet flag."""
        args = parse_args(["-q"])
        assert args.quiet is True

    def test_combined_options(self):
        """Test combining multiple options."""
        args = parse_args(["-a", "1,2", "-o", "/backup", "-q"])
        assert args.account == "1,2"
        assert args.output_dir_flag == "/backup"
        assert args.quiet is True


class TestArgumentValidation:
    """Test argument validation scenarios."""

    def test_account_with_output(self):
        """Test account selection with output directory."""
        args = parse_args(["-a", "1", "/path/to/output"])
        assert args.account == "1"
        assert args.output_dir == "/path/to/output"

    def test_all_with_output(self):
        """Test --all with output directory."""
        args = parse_args(["--all", "-o", "/backup"])
        assert args.all is True
        assert args.output_dir_flag == "/backup"
