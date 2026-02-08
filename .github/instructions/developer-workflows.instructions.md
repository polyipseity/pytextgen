# Developer Workflows

This document describes common development workflows for contributors and
automation (agents) working inside the `pytextgen` submodule.

Local development quick start:

1. Create and activate a virtual environment (Windows example):

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

2. Install development extras (use `uv`):

    ```powershell
    uv sync --dev
    ```

3. Run formatting, linters and tests before committing:

    ```powershell
    uv run ruff check --fix .
    pre-commit run --all-files
    uv run pytest -q
    ```

Script & CI conventions:

- Prefer `uv run` for invoking tools when a `pnpm` wrapper is not used.
- CI workflows should install dependencies deterministically (`uv sync --locked`).
- Ensure tests and ruff checks run on PRs; `AGENTS.md` lists the CI expectations.

Commit conventions:

- Use Conventional Commits (`type(scope): short description`).
- When modifying production code, add or update tests to cover behaviour changes.

Agent & automation rules:

- Agents must run the same format & check steps locally (using `uv` wrappers)
  before making commits or opening PRs. This includes running pre-commit hooks
  and the test suite.
- Agents must ask clarifying questions if intent is ambiguous rather than
  guessing when correctness matters.
