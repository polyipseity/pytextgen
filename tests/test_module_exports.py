"""Tests that every module declares a module-level `__all__` tuple.

This test parses the AST of Python modules to avoid executing top-level code.
It asserts that each `.py` file under `src/`, `tests/`, and `scripts/` files
contains a top-level assignment to `__all__` where the value is a `tuple`
containing only string constants.

Rules enforced:
- `__all__` must be present at module top-level.
- The assigned value must be a `tuple` (not a `list`).
- Each element of the tuple must be a string constant.

This follows repository policy: explicit export lists help make the public
surface self-documenting and avoid accidental exports.
"""

import ast
from collections.abc import AsyncIterator, Iterator

import pytest
from anyio import Path

"""Public API of this test module (empty)."""
__all__ = ()

"""Glob patterns relative to the repository root. Only files matching an
include pattern and no exclude pattern are considered candidates."""
_GLOB_SPEC = """
.agents/skills/**/*.py
src/**/*.py
tests/**/*.py
scripts/**/*.py
"""


def _iter_glob_patterns(spec: str) -> Iterator[tuple[str, bool]]:
    """Parse a gitignore-style, multi-line glob specification.

    The ``spec`` string is interpreted as a sequence of lines applied from
    top to bottom. Empty lines and lines starting with ``#`` are ignored.
    Lines beginning with ``!`` are treated as exclusions.  The function
    yields ``(pattern, is_exclude)`` pairs in the original order.
    """
    for raw in spec.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        is_exclude = line.startswith("!")
        pattern = line[1:] if is_exclude else line
        if not pattern:
            continue
        yield pattern, is_exclude


async def _find_py_files() -> list[Path]:
    """Return sorted Python file paths matching ``_GLOB_SPEC``.

    This mirrors the implementation used in ``test_docstrings`` and
    ``test_git_executable`` so that all three modules share the same logic.
    """
    root = Path(__file__).parent.parent  # repo root
    yielded: set[Path] = set()
    result: list[Path] = []

    async def _iter_files(pattern: str) -> AsyncIterator[Path]:
        """Yield all files matching the given glob pattern, relative to the repo root."""
        async for p in root.glob(pattern):
            if await p.is_file():
                yield p

    for pattern, is_exclude in _iter_glob_patterns(_GLOB_SPEC):
        if is_exclude:
            async for p in root.glob(pattern):
                yielded.discard(p)
                if p in result:
                    result.remove(p)
        else:
            async for p in _iter_files(pattern):
                if p not in yielded:
                    yielded.add(p)
                    result.append(p)
    return sorted(result)


def _has_all_tuple(node: ast.Module) -> tuple[bool, str]:
    """Returns (ok, message)."""
    for stmt in node.body:
        # look for Assign or AnnAssign to __all__
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    val = stmt.value
                    if isinstance(val, ast.Tuple):
                        # ensure all elements are string constants
                        for elt in val.elts:
                            if not (
                                isinstance(elt, ast.Constant)
                                and isinstance(elt.value, str)
                            ):
                                return (
                                    False,
                                    "__all__ must contain only string constants",
                                )
                        return True, "OK"
                    else:
                        return (
                            False,
                            "__all__ must be a tuple (not a list or other type)",
                        )
        elif isinstance(stmt, ast.AnnAssign):
            # unlikely but handle annotated assignment: __all__: tuple[str, ...] = (...)
            target = stmt.target
            if isinstance(target, ast.Name) and target.id == "__all__":
                val = stmt.value
                if isinstance(val, ast.Tuple):
                    for elt in val.elts:
                        if not (
                            isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ):
                            return False, "__all__ must contain only string constants"
                    return True, "OK"
                else:
                    return False, "__all__ must be a tuple (not a list or other type)"
    return False, "__all__ not found"


def _extract_all_tuple(node: ast.Module) -> tuple[str, ...] | None:
    """Return a statically-determined ``__all__`` tuple, if present."""
    for stmt in node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    val = stmt.value
                    if isinstance(val, ast.Tuple):
                        names = tuple(
                            elt.value
                            for elt in val.elts
                            if isinstance(elt, ast.Constant)
                            and isinstance(elt.value, str)
                        )
                        if len(names) == len(val.elts):
                            return names
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id == "__all__":
                val = stmt.value
                if isinstance(val, ast.Tuple):
                    names = tuple(
                        elt.value
                        for elt in val.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    )
                    if len(names) == len(val.elts):
                        return names
    return None


def _iter_defined_top_level_names(node: ast.Module) -> Iterator[str]:
    """Yield names defined at module top level by defs/imports/assignments."""
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield stmt.name
        elif isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    yield target.id
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name):
                yield stmt.target.id
        elif isinstance(stmt, ast.Import):
            for alias in stmt.names:
                yield (
                    alias.asname
                    if alias.asname is not None
                    else alias.name.split(".")[0]
                )
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                if alias.name == "*":
                    continue
                yield alias.asname if alias.asname is not None else alias.name


@pytest.mark.anyio
async def test_all_tuple_present_and_is_tuple() -> None:
    """Assert that every module declares `__all__` as a tuple of strings.

    The test parses AST for each file and reports per-file failures for
    missing or malformed `__all__` assignments.
    """

    failures: list[str] = []

    for path in await _find_py_files():
        # ignore compiled or cache files (shouldn't be any), and exclude vendored/third-party code
        text = await path.read_text(encoding="utf-8")
        try:
            node = ast.parse(text, filename=path)
        except SyntaxError as exc:
            failures.append(f"{path}: SyntaxError: {exc}")
            continue

        ok, msg = _has_all_tuple(node)
        if not ok:
            failures.append(f"{path}: {msg}")

    if failures:
        joined = "\n".join(failures)
        raise AssertionError(f"__all__ compliance failures:\n{joined}")


@pytest.mark.anyio
async def test___all___follows_top_level_imports() -> None:
    """Ensure `__all__` assignment appears after top-level imports.

    For each module, locate the last top-level `import`/`from ... import`
    statement and ensure the earliest `__all__` assignment comes after it.
    This prevents reordering issues where `__all__` is defined before
    imports (which can hide symbols or cause import-time surprises).
    """

    failures: list[str] = []

    for path in await _find_py_files():
        text = await path.read_text(encoding="utf-8")
        try:
            node = ast.parse(text, filename=path)
        except SyntaxError as exc:
            failures.append(f"{path}: SyntaxError: {exc}")
            continue

        # find line number of the last top-level import (0 if none)
        last_import_lineno = 0
        for stmt in node.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                last_import_lineno = max(last_import_lineno, getattr(stmt, "lineno", 0))

        # find all __all__ assignment linenos (if any)
        all_linenos: list[int] = []
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        all_linenos.append(getattr(stmt, "lineno", 0))
            elif isinstance(stmt, ast.AnnAssign):
                target = stmt.target
                if isinstance(target, ast.Name) and target.id == "__all__":
                    all_linenos.append(getattr(stmt, "lineno", 0))

        if not all_linenos:
            # missing __all__ is already reported by the other test
            continue

        first_all_lineno = min(all_linenos)
        if first_all_lineno <= last_import_lineno:
            failures.append(
                f"{path}: __all__ defined at line {first_all_lineno} "
                f"but top-level import at line {last_import_lineno}"
            )

    if failures:
        raise AssertionError("__all__ ordering failures:\n" + "\n".join(failures))


@pytest.mark.anyio
async def test___all___exports_are_defined_unique_and_non_private() -> None:
    """`__all__` entries should be defined, unique, and not private names."""
    failures: list[str] = []

    for path in await _find_py_files():
        text = await path.read_text(encoding="utf-8")
        try:
            node = ast.parse(text, filename=path)
        except SyntaxError as exc:
            failures.append(f"{path}: SyntaxError: {exc}")
            continue

        exported = _extract_all_tuple(node)
        if exported is None:
            continue

        if len(set(exported)) != len(exported):
            failures.append(f"{path}: __all__ contains duplicated names")

        defined = set(_iter_defined_top_level_names(node))
        for name in exported:
            if name.startswith("_") and not (
                name.startswith("__") and name.endswith("__")
            ):
                failures.append(f"{path}: __all__ contains private name {name!r}")
            if name not in defined:
                failures.append(f"{path}: __all__ exports undefined name {name!r}")

    if failures:
        raise AssertionError("__all__ quality failures:\n" + "\n".join(failures))
