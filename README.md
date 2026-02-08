# pytextgen

Generate text using code.

## Setup & Quickstart ✅

Follow these steps to create a reproducible development environment (Windows example):

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies deterministically using `uv` (recommended):

   ```powershell
   uv sync --all-extras --dev  # use `--locked --all-extras --dev` only in CI
   ```

3. Run tests and format/lint via `uv`:

   ```powershell
   uv run pytest -q
   uv run ruff check --fix .
   ```

Note: Commit `uv.lock` to ensure reproducible installs and use `uv` rather than `pip` for deterministic dependency management. 🔧

---

## Commit message linting ✅

This repository enforces conventional commit messages using `commitlint` via a pre-commit hook configured in `prek.toml`.

- We use `alessandrojcm/commitlint-pre-commit-hook` which runs `commitlint` as a `commit-msg` hook (so it inspects the commit message).
- The lint rules live in `commitlint.config.mjs` (converted from the provided mjs config) and extend the conventional config while ignoring Dependabot "Signed-off-by" lines.

Developer setup:

1. Ensure Node.js is installed (needed by `commitlint`). ⚠️
2. Install hooks using the project's dev tooling:

```powershell
uv run prek install
```

CI also runs commitlint on pushes/PRs via `.github/workflows/commitlint.yml`.

If you prefer a pure-Python alternative, consider `gitlint` (can run as `commit-msg`), but we keep `commitlint` here for parity with the existing CI workflow.
