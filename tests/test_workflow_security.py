"""Tests for Codex AutoFix workflow security configuration."""
import yaml
from pathlib import Path


def test_workflow_has_permission_check():
    """Verify workflow includes permission validation step."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "codex-autofix.yml"
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    job = workflow["jobs"]["run"]
    steps = job["steps"]
    
    # Find permission check step
    permission_step = None
    for step in steps:
        if step.get("name") == "Check commenter permissions":
            permission_step = step
            break
    
    assert permission_step is not None, "Missing permission check step"
    assert permission_step.get("if") == "github.event_name == 'issue_comment'"
    assert "getCollaboratorPermissionLevel" in permission_step["uses"] or \
           "getCollaboratorPermissionLevel" in str(permission_step.get("with", {}))


def test_workflow_checks_out_base_branch():
    """Verify workflow checks out base branch, not PR head."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "codex-autofix.yml"
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    job = workflow["jobs"]["run"]
    steps = job["steps"]
    
    # Find checkout step
    checkout_step = None
    for step in steps:
        if "checkout" in step.get("uses", "").lower():
            checkout_step = step
            break
    
    assert checkout_step is not None, "Missing checkout step"
    
    # Verify it checks out base branch
    checkout_with = checkout_step.get("with", {})
    assert "base_ref" in str(checkout_with.get("ref", "")), \
        "Workflow should checkout base branch, not PR head"


def test_workflow_installs_trusted_dependencies_only():
    """Verify workflow only installs dependencies from base branch."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "codex-autofix.yml"
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    job = workflow["jobs"]["run"]
    steps = job["steps"]
    
    # Find install dependencies step
    install_step = None
    for step in steps:
        if "install" in step.get("name", "").lower() and "dependencies" in step.get("name", "").lower():
            install_step = step
            break
    
    assert install_step is not None, "Missing install dependencies step"
    
    # Verify it's labeled as trusted
    assert "trusted" in install_step.get("name", "").lower(), \
        "Install step should indicate it uses trusted dependencies"


def test_workflow_fetches_pr_as_diff():
    """Verify workflow fetches PR changes as diff without checking out."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "codex-autofix.yml"
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    job = workflow["jobs"]["run"]
    steps = job["steps"]
    
    # Find PR fetch step
    fetch_step = None
    for step in steps:
        if "fetch" in step.get("name", "").lower() and "pr" in step.get("name", "").lower():
            fetch_step = step
            break
    
    assert fetch_step is not None, "Missing PR fetch step"
    
    # Verify it creates a diff
    run_command = fetch_step.get("run", "")
    assert "git diff" in run_command, "Should create a diff of PR changes"
    assert "/tmp/pr.diff" in run_command or "pr.diff" in run_command, \
        "Should save diff to file"


def test_workflow_passes_security_parameters():
    """Verify workflow passes security-enhanced parameters to runner."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "codex-autofix.yml"
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    job = workflow["jobs"]["run"]
    steps = job["steps"]
    
    # Find runner execution step
    run_step = None
    for step in steps:
        if "codex_autofix_runner.py" in step.get("run", ""):
            run_step = step
            break
    
    assert run_step is not None, "Missing runner execution step"
    
    run_command = run_step.get("run", "")
    
    # Verify new security parameters
    assert "--base-sha" in run_command, "Should pass base SHA"
    assert "--pr-diff" in run_command, "Should pass PR diff path"


def test_workflow_has_minimal_permissions():
    """Verify workflow uses minimal required permissions."""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "codex-autofix.yml"
    
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)
    
    permissions = workflow.get("permissions", {})
    
    # Should have read for contents, write for PRs
    assert permissions.get("contents") == "read", \
        "Contents permission should be read-only"
    assert permissions.get("pull-requests") == "write", \
        "PR permission needed for posting comments"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
