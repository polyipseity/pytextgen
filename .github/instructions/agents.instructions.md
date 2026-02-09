---
name: AI Agent Runbook
description: Practical, repo-specific guidance for automated contributors and AI agents.
---

<!-- markdownlint-disable-file MD013 MD036 -->

# AI Agent Runbook

This page contains concise, actionable steps and repository-specific rules for AI agents (or other automation) before making changes, opening PRs, or touching non-trivial code.

Quick start (commands you will run every time):

1. Sync & setup

   - uv sync --all-extras --dev
   - prek install

2. Format, lint, and type-check

   - uv run ruff check --fix
   - uv run ruff format
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
- Export control: Public modules that export a surface must define an explicit `__all__` tuple (not a list); test modules must set `__all__ = ()`.

  Export-control policy (detailed):

  - Format and placement: Add a module-level `__all__` tuple placed near the top of the module immediately after imports (the first top-level statements after imports).
  - Use a tuple literal and the exact symbol names (strings) that the module intends to export. Example:

    ```python
    # imports...

    __all__ = (
        "PublicClass",
        "public_function",
    )
    ```

  - What to include: Only include names that are part of the module's public API:
    - Public classes, functions, constants, and names intended for `from module import *`.
    - Do not include private names (names that start with `_`).
    - Re-exported symbols (for example, `from .submodule import Thing`) should be explicitly listed in `__all__` of the parent module.
  - Package `__init__.py`: When a package exposes a public surface via the package import (for example `import package`), set `__all__` in `__init__.py` to the names that should be available at package level (module names or specific symbols). Use tuples there as well.
  - Tests: Test modules must set `__all__ = ()` to make it explicit they export nothing.

  Rationale and checks:

  - **Docstrings:** Every module should start with a brief module-level docstring describing its responsibility. Every public function and class must include a docstring; private helpers should also have docstrings when non-trivial. Follow these simple conventions:

    - Use triple double-quotes ("""Summary line.""") for all docstrings.
    - Start with a one-line summary, followed by an optional description and sections for `Args:`, `Returns:`, `Raises:`, and `Example:` as needed.

    Example:

    ```python
    """Utilities for reading and writing content.

    Args:
        path: Filesystem path handled by the reader.

    Returns:
        A `Reader` instance configured for the path.

    Example:
        >>> Reader.new(path=Path('doc.md'))
    """
    ```

    - Tests should also include a short module docstring and test docstrings describing the intent of the test.
    - Automated checks:
      - Add or update tests if the behaviour or public surface changes.
      - Run `uv run ruff check --fix`, `uv run pyright`, and `uv run pytest` after adding docstrings (these checks are fast and catch formatting/typing issues).

  - Verification: After adding or changing docstrings, run local checks and include the commands you executed in the PR body.
  - Why: Explicit `__all__` makes public surface area explicit for users and tools, reduces accidental exports, and aids static analysis and packaging.
  - Verification: After adding or changing `__all__`, run your local checks (`uv run ruff check --fix`, `uv run pyright`, `uv run pytest`). When adding re-exports, ensure `pyright` and tests still import and reference symbols correctly.
  - Examples and automated checks: Prefer small tests which import the module and assert the presence of promised attributes and absence of private ones when appropriate.
- Typing & dataclasses: Prefer PEP-585/604 annotations (`list[int]`, `str | None`). Many dataclasses use `@dataclass(..., slots=True, frozen=True)`. Do not use `from __future__ import annotations` anywhere in this repository; postponed evaluation of annotations is disallowed. Use explicit forward references or runtime-compatible patterns when necessary.
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

```text
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
