---
name: Testing
description: Test structure, how to write tests, and async testing guidance.
---

<!-- markdownlint-disable-file MD013 MD036 -->

# Testing

Tests use `pytest` and `pytest-asyncio` for async test support. Test configuration is provided in `pyproject.toml` under `[tool.pytest.ini_options]`.

## Test layout and conventions

- All tests live under `tests/` and follow `test_*.py` naming.
- **One test file per source file** is the preferred layout. Mirror the `src/` structure under `tests/` (for example `src/module/sub.py` → `tests/module/test_sub.py`).
- Test modules must define `__all__ = ()` at the top (tests do not export public symbols). See `tests/pytextgen/test___init__.py` for the project-level version parity test.
- All tests and public code must include type annotations and module-level docstrings.
- Agents adding behavior must include tests that follow these conventions and ensure new tests run with `uv run pytest` locally. Use `tmp_path` for filesystem tests and avoid external network calls (mock where appropriate).

## Async tests

- For async code use `async def` tests decorated with `@pytest.mark.asyncio` and `await` coroutines in the test body.
- Do not use `asyncio.run`, `anyio.run`, or similar event-loop wrappers inside tests.

## Running tests locally

```powershell
uv run pytest
# With coverage
uv run pytest --cov=./ --cov-report=term-missing
```

## CI expectations

- CI runs the full test suite and reports coverage. Fast feedback runs a subset of checks; full CI runs the full suite.
- Mark slow or flaky tests appropriately and document mitigation strategies.

## Writing good tests

- Aim for small, deterministic, and fast tests.
- Use fixtures for shared setup. Keep fixture scope appropriate (function or module) for isolation and speed.
- When changing behaviour, add or update tests to cover the change; keep coverage stable or improved.

## Common pitfalls

- Avoid reliance on external services in unit tests; use mocks or recorded responses.
- For filesystem tests, use `tmp_path` fixtures and avoid assumptions about current working directory.
