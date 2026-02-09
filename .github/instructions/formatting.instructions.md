---
name: Formatting & Linters
description: How to run and configure formatters and linters for consistent code style.
---

# Formatting & Linters

This repository uses a small, consistent set of tooling for formatting and linting. The goal is to be fast, deterministic, and easy to run locally and in CI.

## Canonical formatter

- **Ruff** is the canonical Python formatter and linter for this project. Do not add `black` or `isort` to CI or dev tooling; Ruff covers formatting and import ordering.
- **Line length**: 88 characters (configured in `pyproject.toml`).

## Common tasks

- Format repository (auto-fix where possible):

```powershell
uv run ruff check --fix
uv run ruff format
```

- Run static type checks (pyright/Pylance): ensure `pyrightconfig.json` uses `typeCheckingMode: "strict"` for CI parity.

## Editor integration

- Use the editor's Ruff/pyright integration where available. Keep the editor settings consistent with `.editorconfig` and `pyrightconfig.json`.

## Pre-commit-style hooks (prek)

- The repository provides a `prek.toml` (preferred) and still supports `.pre-commit-config.yaml` for compatibility. Install and run locally:

```powershell
uv sync --all-extras --dev
prek install
prek run --all-files
```

- To run a single hook: `prek run <hook-id>` (for example `prek run check-yaml`). You can target specific files with `--files` or run against the whole repo with `--all-files`.

- When a hook is too strict for the repo's needs (for example `forbid-submodules` in a repo that uses submodules intentionally), adjust `prek.toml` or `.pre-commit-config.yaml` accordingly.

### New to pre-commit-style workflows? 💡

Follow this short example to get started with `prek`:

1. Create a configuration

   - Add a `prek.toml` to the repository root. Example snippet:

     ```toml
     [[repos]]
     repo = "https://github.com/pre-commit/pre-commit-hooks"
     rev = "v6.0.0"
     hooks = [ { id = "check-yaml" }, { id = "end-of-file-fixer" } ]
     ```

   Note: `prek` can read `.pre-commit-config.yaml` if you already have one, but `prek.toml` is the native config format.

2. Run hooks on demand

```powershell
prek run
```

- Run a single hook: `prek run <hook-id>` (e.g., `prek run check-yaml`).
- Target specific files with `--files` or run across the whole repository with `--all-files`.

3. Wire hooks into git automatically

```powershell
prek install
```

- `prek install` configures the repository to run `prek run` automatically on commits. Undo with `prek uninstall`.

4. Go further

- Explore the `prek` docs and the underlying hook repositories for advanced configuration and language-specific installers.

## Markdown & other formats

- `rumdl` (high-performance Rust linter/formatter) is the canonical Markdown tool for this repository. It is fast and supports linting and formatting via `rumdl check` and `rumdl fmt`. It auto-discovers existing `markdownlint` configurations (for compatibility) and can import them into the `pyproject.toml` with `rumdl import --pyproject .markdownlint.json`.

- Install & run locally (preferred, via `uv` dev extras):

```powershell
# Ensure dev extras are installed (rumdl is provided from dev extras in pyproject.toml)
uv sync --all-extras --dev

# Lint (fails on violations):
uv run --locked rumdl check

# Auto-fix and report remaining violations:
uv run --locked rumdl check --fix

# Format quietly (exits 0 on success):
uv run --locked rumdl fmt
```

- Use `rumdl` instead of `markdownlint-cli2` for `.md` files. Keep `.markdownlint.jsonc` if you need to preserve the original rules; use `rumdl import --pyproject` to convert an existing markdownlint config into the `[tool.rumdl]` section of `pyproject.toml`.
- `prettier` or other JS formatters are only used if this repository contains files that benefit from them; avoid introducing conflicting formatters for Python files.

## Notes

- Always run formatters and linters before committing to avoid CI failures.
- For large formatting changes, prefer small, focused commits and run the test suite locally after formatting to catch regressions.

Agent note: Agents should not add new formatters (for Python) or change the line-length policy. The canonical tool is Ruff; run `uv run ruff check --fix` and `uv run ruff format` before committing. For type checks run `uv run pyright` and include the results in the PR description.
