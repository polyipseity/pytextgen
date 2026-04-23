---
name: Testing
description: Test structure, how to write tests, and async testing guidance.
---

# Testing

Tests use `pytest` and `pytest-asyncio` for async test support. Test configuration is provided in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Strong baseline expectations (ledger-style)

The pytextgen test suite follows a strict style inspired by `self/ledger`. Keep
these invariants in place:

- Maintain top-level AST safety tests (`tests/test_docstrings.py`,
  `tests/test_module_exports.py`) and extend them when policies change.
- Keep shared fixture wiring in `tests/conftest.py`; centralize reusable,
  typed fixtures in `tests/utils.py`.
- Keep directional source mirroring whenever practical:
  `src/pytextgen/foo/bar.py` → `tests/src/pytextgen/foo/test_bar.py`.
- Every test module must include a module docstring and `__all__ = ()`.
- Prefer deterministic tests: use `tmp_path`, explicit fixture setup, and avoid
  timing-sensitive assertions.
- Exercise both happy-path and failure-path behavior for core code paths,
  including exact exception type and meaningful message checks.

## Test layout and conventions

- All tests live under `tests/` and follow `test_*.py` naming.
- **One test file per source file** is the preferred layout. Mirror the `src/` structure under `tests/` (for example `src/module/sub.py` → `tests/module/test_sub.py`).
- **Capitalization when embedding class names in identifiers:** When a function or test name includes a `ClassName`, embed the class name verbatim using `CamelCase` (for example `test_PythonWriter_writes_result`, `test_ClearWriter_strips_flashcard_state`). Do **not** lowercase or snake*case the class-name portion (avoid `test_pythonwriter*_`or`test*python_writer*_`).
- Test modules must define `__all__ = ()` at the top (tests do not export public symbols) and keep tests focused on observable behaviour. See `tests/pytextgen/test___init__.py` for the project-level version parity test.
- New and updated tests should avoid ad-hoc duplicated helper classes. If a helper
  is reusable across modules, move it into `tests/utils.py` and expose it via
  `pytest_plugins` in `tests/conftest.py`.
- New-folder rule for tests: When adding a new test directory, include an `__init__.py` file in that directory (it may be empty). This guarantees pytest discovery and consistent import semantics for test packages.
  - When changing a module's public API, add or update tests that import the module and assert the exported symbols are present and behave correctly. Prefer updating callers to import directly from the defining submodule rather than relying on re-exports in `__init__.py` when feasible. This helps catch accidental renames or missing re-exports.

- All tests and public code must include type annotations and module-level docstrings.
- Agents adding behavior must include tests that follow these conventions and ensure new tests run with `uv run pytest` locally. Prefer the `tmp_path` fixture for filesystem tests and annotate the parameter as `tmp_path: os.PathLike[str]`. When you need a `Path` object use `Path(tmp_path)`; when passing a path to APIs that expect a `str`, always call `os.fspath(path_like)` (avoid using `str(path_like)` for conversions in library/tests). Avoid external network calls in unit tests (mock where appropriate).

## Async tests

- For async code use `async def` tests decorated with `@pytest.mark.anyio` and `await` coroutines in the test body; when writing helpers prefer Asyncer (`create_task_group`, `soonify`, etc.) instead of raw `asyncio` primitives.
- Do not use `asyncio.run`, `anyio.run`, or similar event-loop wrappers inside tests.

## Priority test matrix for pytextgen

When touching these modules, add or update tests covering both success and
failure paths:

- `src/pytextgen/generate/main.py` and `src/pytextgen/clear/main.py`:
  parser wiring, invoke-path resolution, and exit-code aggregation.
- `src/pytextgen/io/read.py` and `src/pytextgen/io/write.py`:
  parse/read/write behavior, malformed input handling, and deterministic output.
- `src/pytextgen/io/env.py` and `src/pytextgen/io/utils.py`:
  execution semantics, context lifecycle, section parsing, and error messages.
- `src/pytextgen/io/virenv/**`:
  flashcard parsing/formatting edge cases and compatibility re-exports.
- `src/pytextgen/__main__.py`, `src/pytextgen/clear/__main__.py`,
  `src/pytextgen/generate/__main__.py`:
  entrypoint dispatch and runnify wrapper behavior.

## Running tests locally

```powershell
uv run pytest
# With coverage
uv run pytest --cov=./ --cov-report=term-missing

# Focused runs while iterating (examples)
uv run pytest tests/src/pytextgen/io/test_env.py
uv run pytest tests/src/pytextgen/generate/test_main.py -k "exit"
```

Recommended loop while developing:

1. Run focused tests for the edited module(s).
2. Run the full suite.
3. Re-run linters/type checks after test updates (`ruff`, `ty`).

## CI expectations

- CI runs the full test suite and reports coverage. Fast feedback runs a subset of checks; full CI runs the full suite.
- Mark slow or flaky tests appropriately and document mitigation strategies.

## Writing good tests

- Aim for small, deterministic, and fast tests.
- Use fixtures for shared setup. Keep fixture scope appropriate (function or module) for isolation and speed.
- When changing behaviour, add or update tests to cover the change; keep coverage stable or improved.
- When asserting failures, check both the exception type and specific message
  fragments that communicate the root cause.

## Common pitfalls

- Avoid reliance on external services in unit tests; use mocks or recorded responses.
- For filesystem tests, use `tmp_path` fixtures and avoid assumptions about current working directory.
