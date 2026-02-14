# Editing & Formatting Guidelines

This document provides guidance for editing source and documentation files
in a consistent and review-friendly manner.

General rules:

- Use `UTF-8` encoding and preserve newline at end-of-file.
- Keep paragraphs short and wrap commit body lines at **72 characters** (tooling may
  still be configured for 100 characters; prefer 72 as a buffer for clarity).
- Use `README.md` and `AGENTS.md` for high-level project guidance.

Markdown:

- Use consistent heading levels, and add short summaries at the top of docs.
- Prefer fenced code blocks and explicit language markers.
- Use `.markdownlint.jsonc` if present for compatibility, but prefer `rumdl` for Markdown linting and formatting. Add `rumdl` to `[dependency-groups].dev` in `pyproject.toml` and run `uv sync --all-extras --dev` to install it into the project `.venv`; then use `uv run --locked rumdl check`, `uv run --locked rumdl check --fix`, or `uv run --locked rumdl fmt`.

Python style & typing:

- Prefer PEP 585/PEP 604 styles in annotations (e.g., `list[int]`, `str | None`). For abstract collection and iterable protocols (for example `Iterable`, `Iterator`, `Sequence`, `Mapping`, `Collection`, `AsyncIterator`) import from `collections.abc` rather than `typing` (example: `from collections.abc import Iterable, Mapping`). Do not use `from __future__ import annotations`; prefer explicit forward references or runtime-compatible annotations when needed.
- Add module-level docstrings and type annotations for public APIs.
- Add `__all__` tuples to modules that export a public surface and keep test modules explicit with `__all__ = ()`.

  - New-folder rule: when creating any new directory that will contain Python code (production or tests), include an `__init__.py` file in that directory (it may be empty). This applies to both `src/` packages and `tests/` packages to ensure imports, test discovery, and tooling behavior are consistent.

  Details and best practices:

  - Use a tuple literal for `__all__` and place it immediately after imports at the top of the module.
  - Only include intended public names (classes, functions, constants). Avoid including private names (starting with `_`).
  - Prefer not to re-export submodules or symbols from package `__init__.py`. Callers should import directly from the submodule that defines the symbol (for example `from package.module import Thing`). If a package-level API is necessary for a stable, long-lived contract, limit `__all__` to a small set of intentionally exposed names and keep the surface minimal.
  - Keep `__all__` in sync with the module's documentation and public API; update it when refactoring, adding, or removing public symbols.
  - Add or update a simple test that imports the module and asserts the exported symbols exist if the change affects the public surface.

Tests:

- Name tests `test_*.py` and keep them alongside the module under `tests/`.
- When testing async code, use `async def` tests with `@pytest.mark.asyncio`.

Commits & PRs:

- Small, focused commits are easier to review. Use Conventional Commits.
- For agent-generated changes, include the rationale in the commit body when
  deviating from conventions or making non-obvious changes.
- Agents should include the exact commands they ran (format, linter, tests) and a short Todo Plan in the PR description when the change was produced by an automated workflow. Use the repository `agents.instructions.md` for a suggested PR template.
