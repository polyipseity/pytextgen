# Editing & Formatting Guidelines

This document provides guidance for editing source and documentation files
in a consistent and review-friendly manner.

General rules:

- Use `UTF-8` encoding and preserve newline at end-of-file.
- Keep paragraphs short and lines wrapped at 100 characters for commit bodies.
- Use `README.md` and `AGENTS.md` for high-level project guidance.

Markdown:

- Use consistent heading levels, and add short summaries at the top of docs.
- Prefer fenced code blocks and explicit language markers.
- Use `.markdownlint.jsonc` if present for repository enforcement.

Python style & typing:

- Prefer PEP 585/PEP 604 styles in annotations (e.g., `list[int]`, `str | None`).
- Add module-level docstrings and type annotations for public APIs.
- Add `__all__` tuples to modules that export a public surface. Test modules
  should set `__all__ = ()`.

Tests:

- Name tests `test_*.py` and keep them alongside the module under `tests/`.
- When testing async code, use `async def` tests with `@pytest.mark.asyncio`.

Commits & PRs:

- Small, focused commits are easier to review. Use Conventional Commits.
- For agent-generated changes, include the rationale in the commit body when
  deviating from conventions or making non-obvious changes.