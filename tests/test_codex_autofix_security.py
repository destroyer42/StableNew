"""Tests for codex_autofix_runner security enhancements."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add tools directory to path for import
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))


def test_parse_args_with_security_parameters():
    """Test that new security parameters are parsed correctly."""
    # Mock the openai import to avoid dependency
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import parse_args
    
    args = parse_args([
        "--repo", "owner/repo",
        "--pr", "123",
        "--head-sha", "abc123",
        "--base-sha", "def456",
        "--pr-diff", "/tmp/pr.diff",
        "--command", "pytest",
    ])
    
    assert args.repo == "owner/repo"
    assert args.pr == 123
    assert args.head_sha == "abc123"
    assert args.base_sha == "def456"
    assert args.pr_diff == "/tmp/pr.diff"
    assert args.command == "pytest"


def test_gather_repo_snapshot_with_pr_diff():
    """Test that PR diff is included in snapshot when provided."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import gather_repo_snapshot
    
    # Create a temporary diff file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".diff") as f:
        f.write("diff --git a/test.py b/test.py\n")
        f.write("@@ -1,1 +1,1 @@\n")
        f.write("-old line\n")
        f.write("+new line\n")
        diff_path = f.name
    
    try:
        snapshot = gather_repo_snapshot(pr_diff_path=diff_path)
        
        # Verify PR diff is included
        assert "PR Changes" in snapshot
        assert "diff --git a/test.py b/test.py" in snapshot
        assert "+new line" in snapshot
    finally:
        os.unlink(diff_path)


def test_gather_repo_snapshot_without_pr_diff():
    """Test snapshot generation without PR diff (backward compatibility)."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import gather_repo_snapshot
    
    snapshot = gather_repo_snapshot()
    
    # Verify basic snapshot sections exist
    assert "HEAD" in snapshot
    assert "Status" in snapshot or "Tracked files" in snapshot
    # PR Changes should not be present
    assert "PR Changes" not in snapshot


def test_gather_repo_snapshot_with_missing_diff_file():
    """Test snapshot handles missing diff file gracefully."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import gather_repo_snapshot
    
    snapshot = gather_repo_snapshot(pr_diff_path="/nonexistent/file.diff")
    
    # Should not crash, just skip the diff
    assert "HEAD" in snapshot
    # PR Changes should not be present for missing file
    assert "PR Changes" not in snapshot or "Failed to read diff" not in snapshot


def test_parse_args_backward_compatibility():
    """Test that old arguments still work (without new security params)."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import parse_args
    
    args = parse_args([
        "--repo", "owner/repo",
        "--pr", "123",
        "--head-sha", "abc123",
    ])
    
    assert args.repo == "owner/repo"
    assert args.pr == 123
    assert args.head_sha == "abc123"
    # New params should have defaults
    assert args.base_sha == ""
    assert args.pr_diff is None


def test_parse_args_skip_tests_flag():
    """Test that skip-tests flag works."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import parse_args
    
    args = parse_args([
        "--repo", "owner/repo",
        "--pr", "123",
        "--skip-tests",
    ])
    
    assert args.skip_tests is True


def test_run_command_validates_dangerous_chars():
    """Test that run_command rejects commands with dangerous characters."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import run_command
    
    # Test newline rejection
    with pytest.raises(ValueError, match="dangerous characters"):
        run_command("pytest\necho malicious")
    
    # Test backtick rejection
    with pytest.raises(ValueError, match="dangerous characters"):
        run_command("pytest `whoami`")
    
    # Test command substitution rejection
    with pytest.raises(ValueError, match="dangerous characters"):
        run_command("pytest $(whoami)")


def test_run_command_allows_safe_commands():
    """Test that run_command allows legitimate test commands."""
    sys.modules["openai"] = MagicMock()
    
    from codex_autofix_runner import run_command
    
    # These should not raise
    result = run_command("echo test")
    assert result.returncode == 0
    
    result = run_command("pytest --maxfail=1 -q")
    # May fail if pytest not installed, but shouldn't raise ValueError
    assert result.command == "pytest --maxfail=1 -q"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
