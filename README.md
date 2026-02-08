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
   uv sync --dev  # use --locked only in CI
   ```

3. Run tests and format/lint via `uv`:

   ```powershell
   uv run pytest -q
   uv run ruff check --fix .
   ```

Note: Commit `uv.lock` to ensure reproducible installs and use `uv` rather than `pip` for deterministic dependency management. 🔧
