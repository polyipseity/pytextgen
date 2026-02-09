<!-- markdownlint-disable-file MD013 MD036 -->

# Dependencies & Environment

This document explains how dependencies are managed and how to create a
reproducible environment.

Dependency management:

- `pyproject.toml` is the canonical dependency file for Python packages and
  development extras. Use PEP 722 dependency groups for dev extras where
  possible.
- Use `uv` (astral-sh) for deterministic installs and `uv.lock` for reproducible
  install snapshots.

Creating an environment:

1. Create a virtual environment and activate it:

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

2. Install dependencies:

    ```powershell
    uv sync --all-extras --dev
    ```

Notes for CI:

- CI should run `uv sync --locked --all-extras --dev` to install development extras
  deterministically.
- Pin long-lived tooling (for example: `ruff`, `pytest`, `pre-commit`) in the
  `[dependency-groups].dev` section to ensure reproducible behaviour.

When adding a new dependency:

- Add the package to `pyproject.toml` under the appropriate section and run
  `uv sync --all-extras --dev` to update `uv.lock` and commit the lockfile.
- Validate the change locally: run `uv run pytest` and `uv run ruff check --fix .` to ensure the dependency doesn't break type checks or formatting. Agents should record these commands in their PR description and link the updated `uv.lock` entry.
