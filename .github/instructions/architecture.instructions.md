# Architecture & Repository Layout

This document describes the overall layout and important invariants for the
`pytextgen` submodule. Keep it brief and authoritative — other docs may
reference these rules.

Repository layout (top-level view):

- `src/pytextgen/` — package sources.
- `pyproject.toml` — canonical dependency and build metadata.
- `.github/` — workflows, instructions, and agent skills.
- `.pre-commit-config.yaml` — pre-commit hooks for local checks.
- `tests/` — unit tests using `pytest`.
- `docs/` or `README.md` — user-facing documentation and examples.

Important invariants:

- `pyproject.toml` is the canonical source of dependency metadata and build
  configuration. Do not add `requirements.txt` as the primary source of truth.
- Follow the `src/` layout so source files are importable only when installed or
  in a test environment.
- Tests mirror the module layout; one test file per module is preferred.
- Use `uv` (astral-sh) for Python dependency management and `uv.lock` for
  reproducible installs.

If you add new top-level folders, update this document and `AGENTS.md`
references to keep discoverability consistent.