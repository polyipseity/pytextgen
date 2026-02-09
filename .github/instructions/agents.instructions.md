---
name: AI Agent Runbook
description: Practical, repo-specific guidance for automated contributors and AI agents.
---

# AI Agent Runbook

This page contains concise, actionable steps and repository-specific rules for AI agents (or other automation) before making changes, opening PRs, or touching non-trivial code.

Quick start (commands you will run every time):

1. Sync & setup

   - uv sync --all-extras --dev
   - prek install

2. Format, lint, and type-check

   - uv run ruff check --fix .
   - uv run ruff format .
   - uv run pyright

3. Hooks and tests

   - prek run --all-files
   - uv run pytest
   - uv run pytest --cov=./ --cov-report=term-missing (when validating coverage)

Checklist before opening a PR ✅

- All tests pass locally and in CI-equivalent commands.
- Ruff and pyright report no errors or warnings relevant to your change.
- Pre-commit / prek hooks all clean (no unexpected fixes remain).
- Commit messages follow Conventional Commits and release commits are GPG-signed when required.
- The PR description includes: intent, the set of files changed, and any potential upgrade/migration impact.

Repo-specific patterns & examples (do not assume standard patterns):

- Top-level imports only: avoid runtime imports inside functions. See `src/pytextgen/util.py` for the prevalent pattern of aliasing imports with a leading underscore (for example: `from typing import Self as _Self`).
- Export control: Public modules that export a surface must define `__all__`; tests must set `__all__ = ()`.
- Typing & dataclasses: Prefer PEP-585/604 annotations (`list[int]`, `str | None`). Many dataclasses use `@dataclass(..., slots=True, frozen=True)`.
- Async-first code: Many helpers are `async` (use `@pytest.mark.asyncio` for tests). Examples: `CompileCache` context manager in `src/pytextgen/util.py`.
- Formatting toolchain: Ruff is the canonical formatter and linter—do not add `black` or `isort`.
- Version bumps: Update `pyproject.toml` and `src/pytextgen/__init__.py` together. Run the version parity test (`tests/pytextgen/test___init__.py`) and `uv sync --all-extras --dev` so `uv.lock` is updated.

When you need human help 💬

- Ask a short, specific clarifying question rather than making assumptions. If unsure about upgrade/migration trade-offs, prefer to ask rather than guess.
- If a change affects behaviour, include a suggested test and a note in the PR explaining the rationale so reviewers can triage.

Safety & secrets ⚠️

- Never commit secrets or credentials. Use placeholders for examples (UUIDs, example amounts, names).
- If you discover a secret in the repo, stop, redact it from any generated output, and raise it following the repository's `SECURITY.md` guidance immediately.

Workflow tools for agents

- Use the Todo List Tool for multi-step work. Add a concise plan, mark one item `in-progress`, complete it, then move to the next. Example Todo plan:

  1. Add a new test for `foo` (in `tests/pytextgen/test_foo.py`) — in-progress
  2. Implement behaviour in `src/pytextgen/foo.py` — not-started
  3. Run format & tests, fix issues — not-started

- Run the same local checks the CI runs (format, type, tests) before creating a PR. Include the exact commands you executed in the PR body (example: `uv run ruff check --fix . && uv run pyright && uv run pytest`).

Optional PR template snippet (paste into PR description):

```
What I changed:
- <brief summary>

Commands I ran locally:
- uv sync --all-extras --dev
- uv run ruff check --fix .
- uv run pyright
- uv run pytest

Why this change:
- <short rationale>

Tests:
- <test file(s) added/updated>
```

This file is intentionally short and practical. If anything is unclear, ask for clarification and we will extend these steps with concrete examples or tests.
