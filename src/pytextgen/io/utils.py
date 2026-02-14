"""I/O helper types and utilities.

Contains `Location` protocols, `FileSection` logic for extracting and
updating named file sections, and small helpers used by readers/writers.
"""

import re
from abc import ABCMeta, abstractmethod
from asyncio import TaskGroup, create_task
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Mapping
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from functools import cache
from io import StringIO
from itertools import islice
from os import stat
from os.path import splitext
from threading import Lock
from types import MappingProxyType, TracebackType
from typing import (
    Any,
    ClassVar,
    Self,
    TextIO,
    TypeGuard,
    final,
)
from weakref import WeakKeyDictionary

from aioshutil import sync_to_async
from anyio import AsyncFile, Path

from ..meta import NAME, OPEN_TEXT_OPTIONS
from ..utils import (
    abc_subclasshook_check,
    async_lock,
    wrap_async,
)

__all__ = (
    "AnyTextIO",
    "lock_file",
    "Location",
    "NullLocation",
    "NULL_LOCATION",
    "PathLocation",
    "FileSection",
    "Result",
)

AnyTextIO = TextIO | AsyncFile[str]
_FILE_LOCKS = defaultdict[Path, Lock](Lock)
_stat_a = sync_to_async(stat)


@asynccontextmanager
async def lock_file(path: Path) -> AsyncIterator[None]:
    """Async context manager that acquires a per-path lock for safe writes."""
    async with async_lock(_FILE_LOCKS[await path.resolve(strict=True)]):
        yield


class Location(metaclass=ABCMeta):
    """Protocol representing a location that can be opened for IO.

    Concrete implementations should provide an async `open` context manager
    returning an async text file-like object and a `path` property.
    """

    __slots__: ClassVar = ()

    @abstractmethod
    def open(self) -> AbstractAsyncContextManager[AnyTextIO]:
        """Open this `Location` and return an async text file-like context."""
        raise NotImplementedError(self)

    @property
    @abstractmethod
    def path(self) -> Path | None:
        """Return the underlying filesystem `Path` or `None` for `NullLocation`."""
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        """Structural check used by `issubclass` to recognise Location-like types."""
        return abc_subclasshook_check(
            Location, cls, subclass, names=("path", cls.open.__name__)
        )


@final
@Location.register
class NullLocation:
    """A `Location` that provides an in-memory, transient I/O buffer.

    Useful for testing or representing missing targets.
    """

    __slots__: ClassVar = ()

    @asynccontextmanager
    async def open(self) -> AsyncIterator[AnyTextIO]:
        """Return an async context manager yielding a transient text buffer."""
        yield StringIO()

    @property
    def path(self) -> None:
        """`NullLocation` has no filesystem path and returns `None`."""
        return None


assert issubclass(NullLocation, Location)
NULL_LOCATION = NullLocation()


@final
@Location.register
@dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=True,
    slots=True,
)
class PathLocation:
    """A `Location` backed by a filesystem path."""

    path: Path

    @asynccontextmanager
    async def open(self) -> AsyncIterator[AnyTextIO]:
        """Open the underlying filesystem path for read/write access."""
        async with await self.path.open(mode="r+t", **OPEN_TEXT_OPTIONS) as file:
            yield file


assert issubclass(PathLocation, Location)


@final
@Location.register
@dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=True,
    slots=True,
)
class FileSection:
    """Represents a named section inside a file for safe read/write.

    Use `FileSection.find` to locate available sections and `open` to edit
    the contained data using a context manager that persists changes.
    """

    @final
    @dataclass(
        init=True,
        repr=True,
        eq=True,
        order=False,
        unsafe_hash=False,
        frozen=True,
        match_args=True,
        kw_only=True,
        slots=True,
    )
    class SectionFormat:
        """Format description for a named file `FileSection`.

        Holds compiled regexes and the data-extraction callable used to
        identify and extract section content.
        """

        start_regex: re.Pattern[str]
        end_regex: re.Pattern[str]
        start: str
        stop: str
        data: Callable[[re.Match[str]], str]

    SECTION_FORMATS: ClassVar = {
        "": SectionFormat(
            start_regex=re.compile(rf"\[{NAME},generate,([^,\]]*?)\]", re.NOFLAG),
            end_regex=re.compile(rf"\[{NAME},end\]", re.NOFLAG),
            start=f"[{NAME},generate,{{section}}]",
            stop=f"[{NAME},end]",
            data=lambda match: match[1],
        ),
        ".md": SectionFormat(
            start_regex=re.compile(
                rf"""<!--{NAME} generate section=(['"])(.*?)\1-->""", re.DOTALL
            ),
            end_regex=re.compile(rf"<!--/{NAME}-->", re.NOFLAG),
            start=f'<!--{NAME} generate section="{{section}}"-->',
            stop=f"<!--/{NAME}-->",
            data=lambda match: match[2],
        ),
    }

    path: Path
    section: str

    @classmethod
    async def find(cls, path: Path) -> Iterable[str]:
        """Return an iterable of section names present in `path`."""
        return (await _FILE_SECTION_CACHE[path]).sections.keys()

    @asynccontextmanager
    async def open(self) -> AsyncIterator[AnyTextIO]:
        """Return an async context manager for editing this file section."""
        async with (
            _FileSectionIO(self)
            if self.section
            else await self.path.open(mode="r+t", **OPEN_TEXT_OPTIONS)
        ) as file:
            yield file


@final
@dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=True,
    slots=True,
)
class _FileSectionCacheData:
    """Container for cached section metadata and the file's modification time."""

    EMPTY: ClassVar[Self]
    mod_time: int
    sections: Mapping[str, tuple[slice, str]]

    def __post_init__(self):
        """Wrap `sections` in a read-only mapping after construction."""
        object.__setattr__(self, "sections", MappingProxyType(dict(self.sections)))


_FileSectionCacheData.EMPTY = _FileSectionCacheData(mod_time=-1, sections={})


class _FileSectionCache(dict[Path, Awaitable[_FileSectionCacheData]]):
    """Async-aware cache mapping `Path` to `_FileSectionCacheData` awaitables.

    Manages per-path locks to avoid concurrent parses of the same file.
    """

    __slots__: ClassVar = ("__locks",)

    def __init__(self):
        """Initialise the file-section cache with per-path locks."""
        super().__init__()
        self.__locks = WeakKeyDictionary[Path, Callable[[], Lock]]()

    async def __getitem__(self, key: Path):
        """Return cached file-section metadata for `key`, refreshing when stale.

        Parses the file for named sections when the file modification time
        differs from the cached value and returns a `_FileSectionCacheData`
        instance.
        """
        key = await key.resolve(strict=True)
        _, ext = splitext(key)
        try:
            format = FileSection.SECTION_FORMATS[ext]
        except KeyError as ex:
            raise ValueError(f"Unknown extension: {key}") from ex
        async with async_lock(self.__locks.setdefault(key, cache(Lock))()):
            try:
                cache_ = await super().__getitem__(key)
            except KeyError:
                cache_ = _FileSectionCacheData.EMPTY
            try:
                mod_time = (await _stat_a(key)).st_mtime_ns
                if mod_time != cache_.mod_time:
                    async with await key.open(mode="rt", **OPEN_TEXT_OPTIONS) as file:
                        text = await file.read()
                    sections = dict[str, tuple[slice, str]]()
                    read_to = 0
                    for start in format.start_regex.finditer(text):
                        start_idx = start.start()
                        if start.start() < read_to:
                            raise ValueError(
                                f"Overlapping section at char {start.start()}: {key}"
                            )
                        section = format.data(start)
                        if section in sections:
                            raise ValueError(f'Duplicated section "{section}": {key}')
                        end_str = format.stop.format(section=section)
                        try:
                            end_idx = text.index(end_str, start.end())
                        except ValueError as ex:
                            raise ValueError(
                                f"Unenclosure from char {start.start()}: {key}"
                            ) from ex
                        slice0 = slice(start_idx + len(start[0]), end_idx)
                        sections[section] = (slice0, text[slice0])
                        read_to = end_idx + len(end_str)
                    for end in islice(
                        format.end_regex.finditer(text), len(sections), None
                    ):
                        raise ValueError(
                            f"Too many closings at char {end.start()}: {key}"
                        )
                    cache_ = _FileSectionCacheData(
                        mod_time=mod_time,
                        sections=sections,
                    )
            finally:
                cache_ = create_task(
                    wrap_async(cache_)
                )  # Use `create_task` to avoid `RuntimeError` on already-awaited awaitables.`
                super().__setitem__(key, cache_)  # Replenish awaitable
        return (
            await cache_
        )  # Intentionally `await to avoid `RuntimeWarning` on never-awaited awaitables.

    def __setitem__(self, key: Path, value: Awaitable[_FileSectionCacheData]):
        """Prevent external assignment — cache entries must be managed internally."""
        raise TypeError("Unsupported")


_FILE_SECTION_CACHE = _FileSectionCache()


@final
class _FileSectionIO(StringIO):
    """In-memory I/O proxy for editing a `FileSection` safely.

    Provides an async enter/exit lifecycle that persists changes back to disk
    when the context is exited.
    """

    __slots__: ClassVar = ("__closure", "__file", "__slice", "__initial_value")

    def __init__(self, closure: FileSection, /):
        """Initialise an in-memory IO proxy for a `FileSection` instance."""
        self.__closure = closure

    def __enter__(self):
        """Synchronous context manager entry is unsupported for `_FileSectionIO`."""
        raise TypeError("Unsupported")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        """Synchronous context manager exit is unsupported for `_FileSectionIO`."""
        raise TypeError("Unsupported")

    def close(self):
        """Direct close is unsupported; use the async context manager methods."""
        raise TypeError("Unsupported")

    async def aclose(self):
        """Persist any changes made to the in-memory buffer back to disk.

        This method is used by the async context manager exit path to update
        the underlying file section safely and then close the real file.
        """
        try:
            try:

                async def reader():
                    """Read the current file contents asynchronously for comparison."""
                    await self.__file.seek(0)
                    return await self.__file.read()

                read_task = create_task(reader())
                try:
                    self.seek(0)
                    if (text := self.read()) != self.__initial_value:
                        read = await read_task
                        async with TaskGroup() as tg:
                            _ = tg.create_task(self.__file.seek(0))
                            text = f"{read[: self.__slice.start]}{text}{read[self.__slice.stop :]}"
                        await self.__file.write(text)
                        await self.__file.truncate()
                finally:
                    read_task.cancel()
            finally:
                await self.__file.aclose()
        finally:
            super().close()

    async def __aenter__(self) -> "_FileSectionIO":
        """Async-enter: prepare the in-memory buffer with the section's content."""
        self.__file = await self.__closure.path.open(mode="r+t", **OPEN_TEXT_OPTIONS)
        try:
            self.__slice, self.__initial_value = (
                await _FILE_SECTION_CACHE[self.__closure.path]
            ).sections[self.__closure.section]
            super().__init__(self.__initial_value)
            super().__enter__()
        except Exception:
            await self.__file.aclose()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        """Async-exit: persist buffer changes and close underlying file."""
        await self.aclose()


assert issubclass(FileSection, Location)


@final
@dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=True,
    slots=True,
)
class Result:
    """A textual result destined for a `Location`.

    Attributes:
        location: the `Location` to which the text should be written.
        text: the string content to write.
    """

    location: Location
    text: str

    @classmethod
    def isinstance(cls, any: Any) -> TypeGuard[Self]:
        """Type-guard helper that checks whether `any` matches the `Result` shape.

        Returns True when `any` has a `location` implementing `Location` and a
        `text` string attribute; otherwise returns False.
        """
        try:
            return isinstance(any.location, Location) and isinstance(any.text, str)
        except AttributeError:
            return False
