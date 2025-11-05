# Codex AutoFix Workflow

This repository includes an opt-in GitHub Actions workflow that can ask OpenAI Codex to draft a minimal patch when CI fails. The automation is designed for human-in-the-loop usage: Codex suggests a fix in a PR comment, maintainers decide whether to apply it.

## Security Model

The workflow is designed with security-first principles:

- **Permission gating** – Only users with write access to the repository can trigger the workflow via slash commands
- **Trusted code execution** – The workflow runs code from the base branch (trusted), never from untrusted PR branches
- **Dependency isolation** – Only dependencies from the base branch `requirements.txt` are installed
- **Read-only PR analysis** – PR changes are fetched as diffs for analysis without checking out or executing untrusted code
- **Secret protection** – Secrets are only accessible to trusted runner code, not to PR-contributed code

This prevents malicious contributors from:
- Exfiltrating repository secrets (`OPENAI_API_KEY`, `GITHUB_TOKEN`)
- Running arbitrary code with write permissions
- Installing malicious dependencies
- Exploiting the CI/CD pipeline

## Workflow triggers

- **Slash command** – comment `/codex-autofix` on an open pull request (requires write access).
- **Manual run** – trigger the `Codex AutoFix` workflow via *Actions → Codex AutoFix → Run workflow*, providing the PR number (and optionally a custom test command).

When triggered, the workflow:

1. Validates that the triggering user has write access to the repository
2. Checks out the base branch (trusted code)
3. Installs dependencies from the base branch only
4. Fetches PR changes as a diff for analysis (without checking out)
5. Runs the configured test command from the trusted base branch
6. Sends the test output, repo snapshot, and PR diff to the OpenAI `gpt-5-codex` model
7. Posts Codex's response as a PR comment that includes the root cause, a `diff` block, and validation steps

## Required secrets

The workflow needs an OpenAI API key with access to `gpt-5-codex`:

- Add a repository secret named **`OPENAI_API_KEY`** containing the token.
- The default `GITHUB_TOKEN` permission is sufficient for posting PR comments; no additional PAT is required.

## Customization

- Override the test command by supplying the `test_command` input in a manual dispatch. The slash command always uses the default.
- Set the `CODEX_AUTOFIX_COMMAND` environment variable before invoking the runner if you wrap it in another automation.
- Use the `--skip-tests` CLI flag when running `tools/codex_autofix_runner.py` locally to capture context without executing the test suite (for example, if you already have failing logs you want Codex to inspect).
- Use the `--pr-diff` argument to provide a path to a PR diff file for analysis without checking out untrusted code.

## Validation

We validated the workflow on a PR that intentionally broke `tests/test_gui_enhancements.py::test_reset_button_disables_controls`. After commenting `/codex-autofix`:

- The workflow posted a single comment linking back to the run and included the failing pytest command output.
- Codex suggested a two-line patch in `src/gui/components/pipeline_controls.py` that restored the missing `state="disabled"` assignment.
- Re-running `pytest --maxfail=1 -q` on the patched branch passed locally, confirming the fix required no additional edits.

Keep Codex's proposal as a starting point—review, adjust, and commit the changes manually.
