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
uv run --locked ruff check --fix .
uv run --locked ruff format .
```

- Run static type checks (pyright/Pylance): ensure `pyrightconfig.json` uses `typeCheckingMode: "strict"` for CI parity.

## Editor integration

- Use the editor's Ruff/pyright integration where available. Keep the editor settings consistent with `.editorconfig` and `pyrightconfig.json`.

## Pre-commit and lint-staged

- The repository provides `.pre-commit-config.yaml` with recommended `pre-commit-hooks` hooks and a Ruff hook that attempts to fix problems automatically. Install and run locally:

```powershell
uv sync
pre-commit install
pre-commit run --all-files
```

- When a hook is too strict for the repo's needs (for example `forbid-submodules` in a repo that uses submodules intentionally), adjust the `.pre-commit-config.yaml` accordingly.

## Markdown & other formats

- `markdownlint-cli2` is used for `.md` files via lint-staged and CI. Use the project's `.markdownlint.jsonc` configuration for rules and fixes.
- `prettier` or other JS formatters are only used if this repository contains files that benefit from them; avoid introducing conflicting formatters for Python files.

## Notes

- Always run formatters and linters before committing to avoid CI failures.
- For large formatting changes, prefer small, focused commits and run the test suite locally after formatting to catch regressions.
