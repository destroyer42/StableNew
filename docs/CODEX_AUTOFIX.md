# Codex AutoFix Workflow

This repository includes an opt-in GitHub Actions workflow that can ask OpenAI Codex to draft a minimal patch when CI fails. The automation is designed for human-in-the-loop usage: Codex suggests a fix in a PR comment, maintainers decide whether to apply it.

## Workflow triggers

- **Slash command** – comment `/codex-autofix` on an open pull request.
- **Manual run** – trigger the `Codex AutoFix` workflow via *Actions → Codex AutoFix → Run workflow*, providing the PR number (and optionally a custom test command).

When triggered, the workflow:

1. Checks out the PR head commit.
2. Installs the project dependencies together with the `openai` and `requests` client libraries.
3. Runs the configured test command (defaults to `pytest --maxfail=1 -q`).
4. Sends the test output, repo snapshot, and workflow metadata to the OpenAI `gpt-5-codex` model.
5. Posts Codex’s response as a PR comment that includes the root cause, a `diff` block, and validation steps.

## Required secrets

The workflow needs an OpenAI API key with access to `gpt-5-codex`:

- Add a repository secret named **`OPENAI_API_KEY`** containing the token.
- The default `GITHUB_TOKEN` permission is sufficient for posting PR comments; no additional PAT is required.

## Customization

- Override the test command by supplying the `test_command` input in a manual dispatch. The slash command always uses the default.
- Set the `CODEX_AUTOFIX_COMMAND` environment variable before invoking the runner if you wrap it in another automation.
- Use the `--skip-tests` CLI flag when running `tools/codex_autofix_runner.py` locally to capture context without executing the test suite (for example, if you already have failing logs you want Codex to inspect).

## Validation

We validated the workflow on a PR that intentionally broke `tests/test_gui_enhancements.py::test_reset_button_disables_controls`. After commenting `/codex-autofix`:

- The workflow posted a single comment linking back to the run and included the failing pytest command output.
- Codex suggested a two-line patch in `src/gui/components/pipeline_controls.py` that restored the missing `state="disabled"` assignment.
- Re-running `pytest --maxfail=1 -q` on the patched branch passed locally, confirming the fix required no additional edits.

Keep Codex’s proposal as a starting point—review, adjust, and commit the changes manually.
