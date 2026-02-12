<!-- markdownlint-disable MD013 MD036 -->

# pytextgen AGENTS

**IMPORTANT: This documentation must not contain confidential information.** Use non-confidential placeholders for examples (UUIDs, example amounts, names).

## 🚩 Agent Workflow Reminders

**Read relevant skill/instructions before acting.** When asked to perform a skill, read the corresponding SKILL or INSTRUCTIONS file in full before making changes.

**Use the Todo List Tool for multi-step tasks.** Plan steps, mark one step `in-progress`, complete it, then continue. Keep the todo list short and explicit.

**Ask instead of guessing.** If requirements are ambiguous, pause and ask a clarifying question rather than assuming behavior.

## Project Overview

pytextgen is a focused utility for generating programmatic content blocks in Markdown and related formats. It is a small, well-scoped Python package with the following priorities:

- Clear, well-typed public APIs
- Reproducible dev environments via `uv` and PEP 722 dependency groups
- Fast, deterministic linting and formatting via `ruff`
- Comprehensive tests using `pytest` and coverage reports

## Documentation Structure

Store long-form guidance in `.github/instructions/` or `docs/` when appropriate. Recommended instruction pages include (examples):

- `developer-workflows.instructions.md` — Development process, how to run checks, and CI expectations.
- `formatting.instructions.md` — How to run and configure formatters and linters locally.
- `testing.instructions.md` — Test structure, how to write tests, and async testing guidance.
- `release.instructions.md` — Step-by-step release guidance, tagging, and signing.

If you add an instructions file, link to it from this `AGENTS.md`.

## Agent Code Conventions (important) 🔧

- **Top-level imports only.** Avoid runtime or inline imports. Ruff enforces `import-outside-top-level` (PLC0415).
- **Use os.PathLike for file identifiers.** Accept `os.PathLike` and use `os.fspath(path_like)` when a string path is needed.
- **Timezone-aware datetimes.** Use `datetime.now(timezone.utc)` (avoid `datetime.utcnow()`).
- **Type hints:** Prefer PEP 585 types (`dict`, `list`) and `X | Y` unions (PEP 604). Use `Self` where appropriate. Aim for `typeCheckingMode: "strict"` compatibility in `pyrightconfig.json`. Do not use `from __future__ import annotations` in this repository; postponed evaluation of annotations is not permitted.
- **Docstrings & annotations:** All modules, functions, classes (public and private), and tests must include clear module-level and object-level docstrings and complete type annotations. Docstrings should be concise, use triple double-quotes, include a short one-line summary, and expand when necessary to describe parameters, return values, and examples. See the `agents.instructions.md` runbook for a short template and examples.
- **`__all__` usage:** Export control via `__all__` is mandatory; tests should use `__all__ = ()`.

  Detailed rules:

  - Place `__all__` as a tuple literal immediately after imports at the top of the module.
  - Only include public symbols (classes, functions, constants) or package-level module names; do not include names starting with `_`.
  - Prefer not to re-export submodules via package `__init__.py`. Callers should import directly from submodules. When a package-level API is necessary and intentionally stable, prefer centralizing the package's exported surface in a `meta.py` module located in the package directory. Put the exported symbols and the `__all__` tuple in `meta.py` and have `__init__.py` import the minimal exported names (or forward `__all__` from `_meta`) so the package-level surface remains small and explicit.
  - When changing public symbols, update `__all__`, update docs, and add or update tests that verify exports. Run `uv run ruff check --fix`, `uv run pyright`, and `uv run pytest` locally before opening a PR.
- **Async tests:** Prefer `async def` tests with `@pytest.mark.asyncio` and `await` usage. Do not use `asyncio.run` within pytest tests.

## Formatting & tooling note 💡

- **Ruff** is the canonical formatter/linter for Python. Do not add `black` or `isort`. Use:

    ```powershell
    uv run ruff check --fix
    uv run ruff format
    ```

- For Markdown we use **rumdl** (fast Rust-based linter & formatter). Install via dev extras (add `rumdl` to `[dependency-groups].dev` in `pyproject.toml` and run `uv sync --all-extras --dev`) and run `uv run --locked rumdl check` to lint and `uv run --locked rumdl fmt` to format. `rumdl` auto-discovers `.markdownlint.jsonc` and supports `rumdl import --pyproject` to convert existing configs into the `[tool.rumdl]` section of `pyproject.toml`.

- Use `uv` and commit `uv.lock` to ensure reproducible installs.

## Pre-commit-style hooks (prek) and local checks ✅

- Install `prek` as a dev extra and run:

    ```powershell
    uv sync --all-extras --dev
    prek install
    prek run --all-files
    ```

- The repository provides a `prek.toml` (preferred) and still supports `.pre-commit-config.yaml` for compatibility. Recommended checks include `pre-commit-hooks`, `ruff`, `rumdl` (Markdown), and a `pytest` hook run on push.

- `rumdl` provides an official pre-commit hook repository (`rvben/rumdl-pre-commit`) exposing `rumdl` and `rumdl-fmt` hooks; `prek` will install this automatically when present in `prek.toml`.

---

## Tests & CI expectations 🔬

- CI runs linters and tests on PRs. Follow `.github/workflows/ci.yml` for exact steps.
- Tests should mirror the `src/` structure in `tests/`. Prefer one test file per source file unless splitting is justified.
- Use `pytest` and include coverage (`pytest-cov`) reporting. Make sure slow or flaky tests are marked appropriately and documented.

---

## Branching & commit conventions

- Use feature branches (`feat/description`) and `fix/short-description` for bugfixes.
- Follow Conventional Commits for commit messages (type(scope): description). Make sure commit bodies are wrapped to 72 characters or fewer (use 72 as a buffer for human-readability; tooling may still be configured for 100 characters).

---

## Release checklist (semantic versioning)

1. Update the version in `pyproject.toml` (primary) and keep `src/pytextgen/__init__.py` in sync. Ensure both files match and commit them together as a single signed commit with the bare version as the message (e.g., `1.2.3`).

    **Important:** After changing the version, run `uv sync --all-extras --dev` locally to update `uv.lock` and dev extras. If `uv.lock` changes, commit it (for example: `git add uv.lock && git commit -m "chore: update uv.lock"`). In CI prefer `uv sync --locked --all-extras --dev` to validate the locked environment.

    ```powershell
    git add pyproject.toml uv.lock src/pytextgen/__init__.py
    git commit -S -m "1.2.3"
    git tag -s -a v1.2.3 -m "v1.2.3"
    git push origin HEAD
    git push origin --tags
    ```

2. Keep releases minimal and focused; add release notes in a separate commit if needed.

**Note:** We use the `uv_build` backend. Dynamic metadata (for example, reading the version from `__init__.py` via setuptools dynamic config) is not supported by `uv_build`; prefer a static `version` in `pyproject.toml` and keep `src/pytextgen/__init__.py` synced.

---

## CI & Packaging

- CI should reproduce local dev installs via `uv sync --locked --all-extras --dev`.
- Use `uv run -m build` to build source distributions and wheels locally.
- Publish via `twine` using credentials stored in CI secrets; never commit credentials to the repo.

---

## Security & secrets

- Avoid placing secrets in the repo. Use `SECURITY.md` if present to describe responsible disclosure.
- Use `detect-private-key` and `detect-aws-credentials` hooks (via `prek`) to catch accidental leaks. Add or adjust hooks in `prek.toml` or `.pre-commit-config.yaml` for compatibility.

---

## Troubleshooting & Maintainers

- Missing GPG key: ensure your GPG key is available and `gpg` is in PATH. Configure `user.signingkey` in Git.
- Failed tests: run `uv run pytest` locally and inspect failing traces.

**Maintainers:** add contact details (email or GitHub handles) here.

---

## VS Code & Editor Setup

- Use `.editorconfig` for sensible defaults (UTF-8, final newline, trim trailing whitespace).
- Keep `pyrightconfig.json` with `typeCheckingMode: "strict"` to match repository expectations.

---

## Agent Runbook (for AI agents) 🔧

This repository includes an agent-specific runbook to help automated contributors work safely and effectively.

Quick checklist (run before committing or opening a PR):

- Read `.github/instructions/*` (especially `developer-workflows.instructions.md` and `agents.instructions.md`).
- Sync the environment: `uv sync --all-extras --dev` and install hooks: `prek install`.
- Format & lint: `uv run ruff check --fix` and `uv run ruff format`.
- Run pre-commit hooks: `prek run --all-files` (or `pre-commit run --all-files` if using pre-commit).
- Type check: `uv run pyright` (or run your editor's pyright integration configured by `pyrightconfig.json`).
- Run tests: `uv run pytest` (use `--cov` when verifying coverage changes).
- Ensure conventional commit messages and sign release commits (`git commit -S -m "1.2.3"`).

Repository-specific patterns & gotchas:

- Top-level imports only: avoid runtime imports inside functions. Import names normally and avoid aliasing with a leading underscore; for example: `from typing import Self`. Prefer clear, unambiguous imports or import the module when needed to avoid name collisions.
- Use explicit `__all__` for export-control and set `__all__ = ()` in tests. See `tests/pytextgen/test___init__.py` for the version parity test pattern.
- Preferred typing styles: PEP 585 (`list[int]`) and PEP 604 (`str | None`). Use `Self`/`TypedDict` where appropriate.
- Async-first patterns: favor `async def` and `@pytest.mark.asyncio` in tests; use `anyio`/`async` I/O patterns (see `CompileCache` in `src/pytextgen/util.py`).
- Do not add `black` or `isort` to the toolchain—Ruff is the canonical formatter/linter.
- When bumping versions: update `pyproject.toml` and `src/pytextgen/__init__.py`, run tests (see version parity test), and run `uv sync --all-extras --dev` to refresh `uv.lock` before committing.

If uncertain about intent or design, ask a short clarifying question rather than guessing. Use the Todo List Tool for multi-step changes and include the reason in the commit/PR body.

---

## Final notes

- Be conservative: when uncertain, ask a question rather than making assumptions.
- When making behavioral changes, include tests and update docs/instructions appropriately.
- Use the Todo List Tool for multi-step tasks and keep the plan concise and actionable.
