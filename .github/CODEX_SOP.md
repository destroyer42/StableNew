# StableNew – Codex Integration SOP

> **Purpose:** Define how GitHub Copilot / Codex should work on the StableNew repo so changes are safe, traceable, and small enough to review.

---

## How to Use This Document

- **For you (Rob):** Use this as your playbook for when and how to involve Codex, and what to ask it to do.
- **For Codex:** At the start of each Copilot Chat session, paste the “Operating Rules” section and refer back to the recipes in this doc.
- **For contributors (future):** Treat this as the standard for AI-assisted changes to StableNew.

You don’t need to memorize the whole thing. Focus on:

1. The **Operating Rules** section when starting a Codex session.
2. The **Standard Task Recipes** section when you want Codex to apply patches, run tests, or adjust files.

---

## Table of Contents

1. [Overview](#overview)  
2. [Roles and Responsibilities](#roles-and-responsibilities)  
3. [Branch and PR Discipline](#branch-and-pr-discipline)  
4. [File Risk Categories](#file-risk-categories)  
5. [Codex Operating Rules](#codex-operating-rules)  
6. [Standard Task Recipes](#standard-task-recipes)  
   - [Apply a Patch from ChatGPT](#apply-a-patch-from-chatgpt)  
   - [Insert a New Helper Function](#insert-a-new-helper-function)  
   - [Run Tests](#run-tests)  
7. [When Things Go Wrong](#when-things-go-wrong)  
8. [Versioning This SOP](#versioning-this-sop)

---

## Overview

StableNew uses ChatGPT (“GPT”) for design and patch generation, and GitHub Copilot / Codex (“Codex”) for local implementation.

**High-level flow:**

1. GPT produces **designs, diffs, and instructions**.  
2. Codex **applies those diffs exactly** and runs tests.  
3. You review, test, and commit in small, focused PRs.

This SOP exists so that:

- Codex doesn’t “freestyle” large refactors.
- Changes remain small, reviewable, and reversible.
- The GUI and pipeline don’t regress every time we touch them.

---

## Roles and Responsibilities

### You (Rob)

- Decide **what** to build/fix.
- Bring logs, stack traces, prompts, and snippets to GPT.
- Feed GPT’s diffs/specs into Codex.
- Review Codex’s changes and run tests.
- Own branch/PR structure.

### ChatGPT (GPT)

- Analyze code snippets, logs, and prompts you provide.
- Propose **minimal, well-scoped patches** (often as unified diffs).
- Generate:
  - Codex-ready prompts
  - Test adjustments
  - PR descriptions and commit messages
- Help debug test failures and regressions.

### Codex / GitHub Copilot Chat

- Apply diffs **exactly** when requested.
- Perform mechanical edits (rename, move, small refactors).
- Run tests and paste back full output.
- **Do not** redesign core parts of the app without a GPT-approved spec.

---

## Branch and PR Discipline

Always work on a **feature/fix branch**, not directly on `main` or `postGemini`.

**Examples:**

- `feature/randomizer-rng-v2`
- `fix/gui-stop-hang`
- `techdebt/tests-gui-root-fixture`

**Recommended workflow:**

1. From base branch (`postGemini`, `gui_sprint`, etc.):

   ```bash
   git checkout -b fix/randomizer-matrix-rng-v2
