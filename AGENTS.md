# pytextgen AGENTS

Treat this folder as the project root. This document describes repository conventions, developer workflow, and release steps for the pytextgen submodule.

## Purpose

pytextgen is a utility for generating programmatic content blocks in Markdown notes. This AGENTS.md is intended for maintainers and contributors working inside this submodule.

## Repository layout (top-level view)

- `__init__.py` — package version and package metadata (update this when releasing).
- `pyproject.toml` (canonical) — use `[dependency-groups].dev` for development extras; `requirements.txt` is deprecated in favor of `pyproject.toml`.
- `tests/` — unit tests (pytest by default, if present).
- `docs/` or `README.md` — usage and examples (if present).

Adjust the list above to match this submodule; paths below assume this folder is the repo root.

## Dependencies

- Declare project dependencies in `pyproject.toml` (this is the authoritative source).
- If `requirements.txt` exists in this repository it is a compatibility/delegation helper and should not be treated as the authoritative dependency list — it delegates to `setup.py`/packaging and does not itself store the canonical dependencies.

## Quick start (development)

1. Create and activate a Python virtual environment (Windows example):

    ```powershell
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```

2. Install development dependencies (recommended):

    ```powershell
    # Using PEP 722 dependency groups (preferred)
    # Add dev extras to `pyproject.toml` (under [dependency-groups].dev), then install:
    uv sync

    # or, if using older tooling, install the editable package with extras
    # (not recommended; prefer `uv sync`)
    ```

3. Run tests (if tests exist):

    ```powershell
    uv run --locked pytest -q
    ```

## Formatting & linting

- Recommended tools: `ruff`, `flake8`, `mypy` (use if configuration files are present).
- To run formatters locally:

    ```powershell
    # Ensure ruff is in dev extras and run via uv for reproducibility
    uv run --locked ruff check --fix .
    uv run --locked ruff format .
    ```

## Pre-commit hooks

Use `pre-commit` to install hooks locally if a `.pre-commit-config.yaml` exists:

```powershell
# Add pre-commit to dev extras, then:
uv sync
pre-commit install
pre-commit run --all-files
```

## Branching & pull request workflow

- Work on feature branches named `feat/description` or `fix/short-description`.
- Use Conventional Commits for commit messages (type(scope): description).
- Ensure tests and linters pass before opening a PR. Include a concise summary and list of changes in the PR description.

## Release checklist (semantic versioning)

When publishing a new release, follow these steps and keep the release commit minimal:

1. Update the version string in `__init__.py` to the new semantic version (e.g. `1.2.3`). Edit only this file in the release commit.

2. Commit the change with the commit message equal to the bare version string (no prefix). The commit must be GPG-signed.

    ```powershell
    git add __init__.py
    git commit -S -m "1.2.3"
    ```

3. Create a signed, annotated tag with the `v` prefix matching the version:

    ```powershell
    git tag -s -a v1.2.3 -m "v1.2.3"
    ```

4. Push the commit and tags to the remote:

    ```powershell
    git push origin HEAD
    git push origin --tags
    ```

Notes:

- Keep the release commit atomic (only version bump). Use separate Conventional Commit changes for other work.
- The tag must be signed to support reproducible release verification.

## Changelog and release notes

- Maintain a `CHANGELOG.md` or use an automated changelog generator based on Conventional Commits.
- If you add release notes, do so in a separate commit (e.g., `chore(release): add release notes for 1.2.3`).

## CI expectations

- CI should run tests, linters, and formatting checks on PRs. If a CI workflow file exists, follow its requirements.

## Packaging & publishing (optional)

- To build artifacts locally:

    ```powershell
    # Add build to dev extras and run via uv
    uv run --locked -m build
    ```

- To publish to PyPI, use `twine` and keep credentials out of the repo (use CI secrets):

    ```powershell
    # Add twine to dev extras and run via uv
    uv run --locked -m twine upload dist/*
    ```

## Security and reporting

- Report security issues privately to the maintainers. If there's a `SECURITY.md`, follow its instructions.

## Contributor guidelines

- Follow the Conventional Commits convention, add tests for new behavior, and include short documentation/examples.

## GPG and signed commits/tags

- This project requires signed release commits and annotated tags. To sign commits and tags, configure your GPG key and set `user.signingkey` in git config.

    Example commit verification:

    ```powershell
    git verify-commit HEAD
    git verify-tag v1.2.3
    ```

## Using this submodule from the parent repo

- When you update the submodule in the parent repository, update the submodule pointer and commit in the parent repo:

    ```powershell
    git submodule update --remote --merge
    git add .
    git commit -m "chore(submodules): update pytextgen to v1.2.3"
    ```

## Badges & metadata

- Optionally add CI, PyPI, and coverage badges to the top of `README.md` for quick status visibility.

## Troubleshooting

- Missing GPG key: ensure your key is available to Git and that `gpg` is in PATH.
- Failed tests: run `pytest -q` locally; ensure dependencies are installed in the venv.

## Maintainers

- List of maintainers or contact details (add e-mail or GitHub handles here).
