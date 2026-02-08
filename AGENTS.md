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
- **Type hints:** Prefer PEP 585 types (`dict`, `list`) and `X | Y` unions (PEP 604). Use `Self` where appropriate. Aim for `typeCheckingMode: "strict"` compatibility in `pyrightconfig.json`.
- **Docstrings & annotations:** Public modules, functions, classes, and tests must include module-level docstrings and complete type annotations.
- **__all__ usage:** Export control via `__all__` is mandatory; tests should use `__all__ = ()`.
- **Async tests:** Prefer `async def` tests with `@pytest.mark.asyncio` and `await` usage. Do not use `asyncio.run` within pytest tests.

## Formatting & tooling note 💡

- **Ruff** is the canonical formatter/linter. Do not add `black` or `isort`. Use:

    ```powershell
    uv run ruff check --fix .
    uv run ruff format .
    ```

- Use `uv` and commit `uv.lock` to ensure reproducible installs.

## Pre-commit hooks and local checks ✅

- Install `pre-commit` as a dev extra and run:

    ```powershell
    uv sync
    pre-commit install
    pre-commit run --all-files
    ```

- The repository provides a `.pre-commit-config.yaml` with the recommended checks from `pre-commit-hooks`, `ruff`, and a `pytest` hook run on push.

---

## Tests & CI expectations 🔬

- CI runs linters and tests on PRs. Follow `.github/workflows/ci.yml` for exact steps.
- Tests should mirror the `src/` structure in `tests/`. Prefer one test file per source file unless splitting is justified.
- Use `pytest` and include coverage (`pytest-cov`) reporting. Make sure slow or flaky tests are marked appropriately and documented.

---

## Branching & commit conventions

- Use feature branches (`feat/description`) and `fix/short-description` for bugfixes.
- Follow Conventional Commits for commit messages (type(scope): description). Make sure commit bodies are wrapped to 100 characters or fewer.

---

## Release checklist (semantic versioning)

1. Update the version in `pytextgen/__init__.py` only.
2. Commit the version bump as a single, signed commit with the bare version as the message (e.g., `1.2.3`).

    ```powershell
    git add pytextgen/__init__.py
    git commit -S -m "1.2.3"
    git tag -s -a v1.2.3 -m "v1.2.3"
    git push origin HEAD
    git push origin --tags
    ```

3. Keep releases minimal and focused; add release notes in a separate commit if needed.

---

## CI & Packaging

- CI should reproduce local dev installs via `uv sync --locked --all-extras --dev`.
- Use `uv run -m build` to build source distributions and wheels locally.
- Publish via `twine` using credentials stored in CI secrets; never commit credentials to the repo.

---

## Security & secrets

- Avoid placing secrets in the repo. Use `SECURITY.md` if present to describe responsible disclosure.
- Use `detect-private-key` and `detect-aws-credentials` pre-commit hooks to catch accidental leaks.

---

## Troubleshooting & Maintainers

- Missing GPG key: ensure your GPG key is available and `gpg` is in PATH. Configure `user.signingkey` in Git.
- Failed tests: run `uv run pytest -q` locally and inspect failing traces.

**Maintainers:** add contact details (email or GitHub handles) here.

---

## VS Code & Editor Setup

- Use `.editorconfig` for sensible defaults (UTF-8, final newline, trim trailing whitespace).
- Keep `pyrightconfig.json` with `typeCheckingMode: "strict"` to match repository expectations.

---

## Final notes

- Be conservative: when uncertain, ask a question rather than making assumptions.
- When making behavioral changes, include tests and update docs/instructions appropriately.
- Use the Todo List Tool for multi-step tasks and keep the plan concise and actionable.



