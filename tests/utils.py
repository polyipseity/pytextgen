"""Shared typed fixtures used across the pytextgen test suite.

This module mirrors the repository-level fixture style used in sibling
projects: it exposes reusable helpers for async file-like paths and module
entry-point execution.
"""

import runpy
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from os import PathLike, fspath
from typing import Any, Literal, Protocol, Self, overload

import asyncer
import pytest
from anyio import Path

"""Public symbols exported by this module."""
__all__ = (
    "AsyncFileFactory",
    "RunModuleHelper",
    "async_file_factory",
    "run_module_helper",
)


class AsyncFileBase(ABC):
    """Minimal async text file protocol used by filesystem-related tests."""

    @abstractmethod
    async def read(self) -> str:
        """Read and return the current text contents."""
        ...

    @abstractmethod
    async def write(self, data: str) -> int:
        """Write ``data`` and return the number of written characters."""
        ...

    @abstractmethod
    async def seek(self, offset: int, whence: int = 0) -> int:
        """Move the file pointer and return the resulting offset."""
        ...

    @abstractmethod
    async def truncate(self) -> None:
        """Truncate the current file stream."""
        ...

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Enter an async context and return this file object."""
        ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> bool:
        """Exit an async context; return ``False`` to propagate exceptions."""
        ...


class AsyncPathBase(ABC):
    """Base class for async path-like values returned by the test factory."""

    last_written: str | None

    @abstractmethod
    async def open(
        self,
        mode: str = "r+t",
        encoding: str = "UTF-8",
        errors: str = "strict",
        newline: str | None = None,
    ) -> AsyncFileBase:
        """Open and return an :class:`AsyncFileBase` instance."""
        ...


class AsyncFileFactory(Protocol):
    """Callable factory returning async path-like wrappers for tests."""

    @overload
    def __call__(self, kind: Literal["disk"], arg: PathLike[str]) -> AsyncPathBase:
        """Create a disk-backed async path wrapper."""
        ...

    @overload
    def __call__(self, kind: Literal["memory"], arg: str) -> AsyncPathBase:
        """Create an in-memory async path wrapper."""
        ...

    def __call__(
        self,
        kind: Literal["disk", "memory"],
        arg: PathLike[str] | str,
    ) -> AsyncPathBase:
        """Create an async path wrapper for the requested ``kind``."""
        ...


@pytest.fixture
def async_file_factory() -> AsyncFileFactory:
    """Return a factory for disk-backed and memory-backed async paths."""

    class DiskAsyncPath(AsyncPathBase):
        """AnyIO ``Path``-backed async path wrapper used by tests."""

        class AsyncFile(AsyncFileBase):
            """Async file wrapper around a real filesystem path."""

            def __init__(self, path: "DiskAsyncPath") -> None:
                """Store the owning path wrapper."""
                self._path = path

            async def read(self) -> str:
                """Read text from disk asynchronously."""
                return await self._path._path.read_text(encoding="utf-8")

            async def write(self, data: str) -> int:
                """Write text to disk and record the latest payload."""
                self._path.last_written = data
                await self._path._path.write_text(data, encoding="utf-8")
                return len(data)

            async def seek(self, offset: int, whence: int = 0) -> int:
                """No-op seek implementation for fixture compatibility."""
                return 0

            async def truncate(self) -> None:
                """No-op truncate implementation for fixture compatibility."""
                return None

            async def __aenter__(self) -> Self:
                """Return the async file wrapper itself."""
                return self

            async def __aexit__(
                self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                tb: object | None,
            ) -> bool:
                """Do not suppress exceptions."""
                return False

        def __init__(self, path: PathLike[str]) -> None:
            """Store a filesystem path for disk-backed operations."""
            self._path = Path(path)
            self.last_written: str | None = None

        async def open(
            self,
            mode: str = "r+t",
            encoding: str = "UTF-8",
            errors: str = "strict",
            newline: str | None = None,
        ) -> AsyncFileBase:
            """Return an async file wrapper bound to this disk path."""
            return self.AsyncFile(self)

    class InMemoryAsyncPath(AsyncPathBase):
        """In-memory async path wrapper used by tests."""

        class AsyncFile(AsyncFileBase):
            """Async file wrapper over in-memory text."""

            def __init__(self, path: "InMemoryAsyncPath") -> None:
                """Store the owning memory-path wrapper."""
                self._path = path

            async def read(self) -> str:
                """Return in-memory text content."""
                return self._path._text

            async def write(self, data: str) -> int:
                """Overwrite in-memory text and record latest payload."""
                self._path.last_written = data
                self._path._text = data
                return len(data)

            async def seek(self, offset: int, whence: int = 0) -> int:
                """No-op seek implementation for fixture compatibility."""
                return 0

            async def truncate(self) -> None:
                """No-op truncate implementation for fixture compatibility."""
                return None

            async def __aenter__(self) -> Self:
                """Return the async file wrapper itself."""
                return self

            async def __aexit__(
                self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                tb: object | None,
            ) -> bool:
                """Do not suppress exceptions."""
                return False

        def __init__(self, text: str) -> None:
            """Store initial in-memory text content."""
            self._text = text
            self.last_written: str | None = None

        async def open(
            self,
            mode: str = "r+t",
            encoding: str = "UTF-8",
            errors: str = "strict",
            newline: str | None = None,
        ) -> AsyncFileBase:
            """Return an async file wrapper bound to this memory path."""
            return self.AsyncFile(self)

    @overload
    def factory(kind: Literal["disk"], arg: PathLike[str]) -> AsyncPathBase:
        """Construct a disk-backed async path wrapper."""
        ...

    @overload
    def factory(kind: Literal["memory"], arg: str) -> AsyncPathBase:
        """Construct an in-memory async path wrapper."""
        ...

    def factory(
        kind: Literal["disk", "memory"], arg: PathLike[str] | str
    ) -> AsyncPathBase:
        """Construct a disk-backed or memory-backed async path wrapper."""
        if kind == "disk":
            if not isinstance(arg, PathLike):
                raise TypeError("disk factory requires os.PathLike input")
            return DiskAsyncPath(fspath(arg))
        if kind == "memory":
            if not isinstance(arg, str):
                raise TypeError("memory factory requires string input")
            return InMemoryAsyncPath(arg)
        raise ValueError(kind)

    return factory


class RunModuleHelper(ABC):
    """Protocol-style helper for running modules under ``__main__``."""

    @abstractmethod
    def __call__(self, module_name: str, argv: list[str]) -> dict[str, bool]:
        """Run the target module and return a dict including ``ran``."""
        ...


@pytest.fixture
def run_module_helper(monkeypatch: pytest.MonkeyPatch) -> RunModuleHelper:
    """Return a helper that runs modules with a safe fake ``asyncer.runnify``."""

    class _RunModule(RunModuleHelper):
        """Module runner that intercepts ``runnify`` to avoid real loop startup."""

        def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
            """Store the monkeypatch instance used for temporary patches."""
            self._monkeypatch = monkeypatch

        def __call__(self, module_name: str, argv: list[str]) -> dict[str, bool]:
            """Execute ``module_name`` as ``__main__`` and report invocation."""
            called: dict[str, bool] = {"ran": False}

            def fake_runnify(
                async_func: Callable[..., Any],
                *_args: object,
                **_kwargs: object,
            ) -> Callable[..., Any]:
                """Mark execution and close returned coroutine to avoid warnings."""
                called["ran"] = True

                def wrapper(*args: Any, **kwargs: Any) -> None:
                    """Execute async callable once and close coroutine immediately."""
                    try:
                        coro = async_func(*args, **kwargs)
                        coro.close()
                    except Exception:
                        pass

                return wrapper

            self._monkeypatch.setattr(asyncer, "runnify", fake_runnify)
            prev_argv = sys.argv[:]
            try:
                sys.argv[:] = argv
                sys.modules.pop(module_name, None)
                runpy.run_module(module_name, run_name="__main__")
            finally:
                sys.argv[:] = prev_argv
            return called

    return _RunModule(monkeypatch)
