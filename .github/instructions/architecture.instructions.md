<!-- markdownlint-disable-file MD013 MD036 -->

# Architecture & Repository Layout

This document describes the overall layout and important invariants for the
`pytextgen` submodule. Keep it brief and authoritative — other docs may
reference these rules.

Repository layout (top-level view):

- `src/pytextgen/` — package sources.
- `pyproject.toml` — canonical dependency and build metadata.
- `.github/` — workflows, instructions, and agent skills.
- `prek.toml` — pre-commit-style hooks configuration for local checks (preferred). The repository continues to include `.pre-commit-config.yaml` for compatibility.
- `tests/` — unit tests using `pytest`.
- `docs/` or `README.md` — user-facing documentation and examples.

Important invariants:

- `pyproject.toml` is the canonical source of dependency metadata and build
  configuration. Do not add `requirements.txt` as the primary source of truth.
- Follow the `src/` layout so source files are importable only when installed or
  in a test environment.
- Tests mirror the module layout; one test file per module is preferred.
- New-folder rule: when creating any new directory that will contain Python code (source or tests), include an `__init__.py` file (it may be empty). This ensures package semantics, reliable imports, and pytest discovery.
- Use `uv` (astral-sh) for Python dependency management and `uv.lock` for
  reproducible installs.

If you add new top-level folders, update this document and `AGENTS.md`.

Agent note: For AI agents and automation, consult `.github/instructions/agents.instructions.md` for a short runbook that includes pre-PR checks and repo-specific patterns (for example: the package follows an async-first approach and uses import aliasing conventions in `src/pytextgen/util.py`).

Key component callouts:

- `src/pytextgen/io/` — environment and file I/O helpers used throughout the package.
- `src/pytextgen/generate/` — generation backends for content units.
- `src/pytextgen/clear/` — small CLI utilities (commands follow the same typing and testing conventions).

Keep this document small and authoritative; add examples above only when they help newcomers find the most relevant files quickly.
references to keep discoverability consistent.
