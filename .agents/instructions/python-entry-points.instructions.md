---
name: Python entry points
description: Convention for writing Python scripts and modules with __name__ == "__main__" entry points
applyTo: "**/*.py"
---

# Python Entry Points Convention (pytextgen)

This document establishes the convention for Python scripts and modules in the pytextgen project that expose entry points for direct execution. All `__main__.py` modules must follow this pattern.

**Inheritance note:** This project largely follows the parent repository's Python entry points convention (see `../../../../.agents/instructions/python-entry-points.instructions.md`). Refer to that document for comprehensive guidance. This file provides pytextgen-specific context and highlights key patterns used in the project.

## Standard Pattern (Async)

```python
"""Module purpose and usage."""

import sys
from asyncer import runnify


async def main(argv: list[str] | None = None) -> None:
    """Main async entry point.

    Args:
        argv: Command-line arguments; defaults to sys.argv[1:] if None.
    """
    if argv is None:
        argv = sys.argv[1:]

    # Application logic here
    pass


def __main__() -> None:
    """Entry point for running the module directly."""
    runnify(main, backend_options={"use_uvloop": True})()


if __name__ == "__main__":
    __main__()
```

## Standard Pattern (Sync)

```python
"""Module purpose and usage."""

import sys


def main(argv: list[str] | None = None) -> None:
    """Main sync entry point.

    Args:
        argv: Command-line arguments; defaults to sys.argv[1:] if None.
    """
    if argv is None:
        argv = sys.argv[1:]

    # Application logic here
    pass


def __main__() -> None:
    """Entry point for running the module directly."""
    main()


if __name__ == "__main__":
    __main__()
```

## Pytextgen-Specific Rules

1. **Module structure**: The pytextgen package uses `__main__.py` files for subcommands (e.g., `src/pytextgen/__main__.py`, `src/pytextgen/generate/__main__.py`, `src/pytextgen/clear/__main__.py`). Each module follows the same entry-point pattern.

2. **Argument handling**: Pytextgen subcommands parse arguments via argparse inside `main()`. All subcommands accept optional `argv` for testing compatibility.

3. **Error handling**: Use consistent exit codes:
   - `0`: Success
   - `1`: General/processing error
   - `2`: Argument parsing error
   - `3`: File/IO error

4. **Type hints**: Include complete type hints on `main()` and `__main__()` functions. Use `ast.Sequence[str]` or similar for argument lists.

5. **Docstrings**: Include module-level and function docstrings explaining purpose, usage, and key parameters. Example:

   ```python
   """Generate pytextgen-fenced content in Markdown files.

   Usage:
       python -m pytextgen.generate --help

   Discovers .md files, regenerates fenced Python code and flashcards,
   and normalizes newlines before writing.
   """
   ```

6. **Testing**: Import `main` directly in tests; do not trigger the entry-point guard:

   ```python
   @pytest.mark.anyio
   async def test_main_with_paths():
       from pytextgen.generate.__main__ import main
       await main(["path/to/file.md"])
   ```

## Pytextgen Entry Points Examples

### Main Module (**main**.py)

```python
"""Pytextgen: programmatically-generated content in Markdown."""

import sys
from asyncer import runnify


async def main(argv: list[str] | None = None) -> None:
    """Main entry point for pytextgen package.

    Routes to subcommands (generate, clear) based on argv[0].
    """
    if argv is None:
        argv = sys.argv[1:]

    # Dispatcher logic: delegate to subcommands
    # (implementation details omitted)
    pass


def __main__() -> None:
    """Entry point for running the module directly."""
    runnify(main, backend_options={"use_uvloop": True})()


if __name__ == "__main__":
    __main__()
```

### Subcommand Module (generate/**main**.py)

```python
"""Generate pytextgen-fenced content in Markdown files.

Usage:
    python -m pytextgen.generate [--help] [FLAGS] [paths...]

Scans .md files for pytextgen fences, regenerates content,
and writes the results back to disk.
"""

import sys
from pathlib import Path
from asyncer import runnify, asyncify
import argparse

__all__ = ("main",)


async def main(argv: list[str] | None = None) -> None:
    """Main async entry point for generation.

    Args:
        argv: Command-line arguments (paths and flags).
    """
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Generate pytextgen content")
    parser.add_argument("paths", nargs="*", help="Paths to files/directories")
    parser.add_argument("-C", "--no-cached", action="store_true", help="Skip cache")
    parser.add_argument("--no-code-cache", action="store_true", help="Skip code cache")
    args = parser.parse_args(argv)

    # Generation logic (wrapped with asyncify for blocking I/O)
    try:
        # ... implementation ...
        return exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return exit(1)


def __main__() -> None:
    """Entry point for running the module directly."""
    runnify(main, backend_options={"use_uvloop": True})()


if __name__ == "__main__":
    __main__()
```

## Implementation Checklist

When creating or updating a pytextgen `__main__.py`:

- [ ] Define `main()` as the primary logic (async or sync)
- [ ] Accept optional `argv: Sequence[str] | None = None` in `main()`
- [ ] Define `__main__()` sync wrapper (with `runnify` for async)
- [ ] Place `if __name__ == "__main__":` guard at end
- [ ] Include return type hints (`-> None` is typical)
- [ ] Add module-level docstring with usage example
- [ ] Add docstrings to `main()` and `__main__()`
- [ ] Use appropriate exit codes (0, 1, 2, 3)
- [ ] Test by importing `main()` directly in pytest with `@pytest.mark.anyio`
- [ ] Run `pyright`, `ruff check`, and `pytest` before committing

## Integration with Parent Convention

For comprehensive guidance on entry points, async patterns, and error handling, see the parent repository's convention:

**File:** `../../../../.agents/instructions/python-entry-points.instructions.md`

**Key sections:**

- Detailed rationale and background
- Integration with argparse and Click
- Comprehensive testing patterns
- Error handling best practices
- Asyncer helper functions reference

## Related Documentation

- `developer-workflows.instructions.md` — Testing and local development
- `testing.instructions.md` — Test structure and pytest patterns
- `formatting.instructions.md` — Code style and linting
- Parent AGENTS.md async guidance — Core async/concurrency patterns
