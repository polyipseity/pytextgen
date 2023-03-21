# -*- coding: UTF-8 -*-
import abc as _abc
import anyio as _anyio
import asyncio as _asyncio
import asyncstdlib as _asyncstdlib
import collections as _collections
import contextlib as _contextlib
import dataclasses as _dataclasses
import functools as _functools
import io as _io
import itertools as _itertools
import os as _os
import re as _re
import threading as _threading
import types as _types
import typing as _typing
import weakref as _weakref

from .. import globals as _globals
from .. import util as _util

AnyTextIO = _typing.TextIO | _anyio.AsyncFile[str]
_FILE_LOCKS = _collections.defaultdict[_anyio.Path, _threading.Lock](_threading.Lock)


@_contextlib.asynccontextmanager
async def lock_file(path: _anyio.Path):
    async with _util.async_lock(_FILE_LOCKS[await path.resolve(strict=True)]):
        yield


class Location(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_abc.abstractmethod
    def open(
        self,
    ) -> _contextlib.AbstractAsyncContextManager[AnyTextIO]:
        raise NotImplementedError(self)

    @property
    @_abc.abstractmethod
    def path(self) -> _anyio.Path | None:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return _util.abc_subclasshook_check(
            Location,
            cls,
            subclass,
            names=(
                "path",
                cls.open.__name__,
            ),
        )


@_typing.final
class NullLocation:
    __slots__: _typing.ClassVar = ()

    @_contextlib.asynccontextmanager
    async def open(self):
        yield _io.StringIO()

    @property
    def path(self):
        return None


Location.register(NullLocation)
assert issubclass(NullLocation, Location)
NULL_LOCATION = NullLocation()


@_typing.final
@_dataclasses.dataclass(
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
    path: _anyio.Path

    @_contextlib.asynccontextmanager
    async def open(self):
        async with await _anyio.open_file(
            self.path, mode="r+t", **_globals.OPEN_OPTIONS
        ) as file:
            yield file


Location.register(PathLocation)
assert issubclass(PathLocation, Location)


@_typing.final
@_dataclasses.dataclass(
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
    @_typing.final
    @_dataclasses.dataclass(
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
        start_regex: _re.Pattern[str]
        end_regex: _re.Pattern[str]
        start: str
        stop: str
        data: _typing.Callable[[_re.Match[str]], str]

    SECTION_FORMATS: _typing.ClassVar[
        _typing.Mapping[str, SectionFormat]
    ] = _types.MappingProxyType(
        {
            "": SectionFormat(
                start_regex=_re.compile(
                    rf"\[{_globals.UUID},generate,([^,\]]*?)\]", flags=_re.NOFLAG
                ),
                end_regex=_re.compile(rf"\[{_globals.UUID},end\]", flags=_re.NOFLAG),
                start=f"[{_globals.UUID},generate,{{section}}]",
                stop=f"[{_globals.UUID},end]",
                data=lambda match: match[1],
            ),
            ".md": SectionFormat(
                start_regex=_re.compile(
                    rf"""<!--{_globals.UUID} generate section=(["'])(.*?)\1-->""",
                    flags=_re.DOTALL,
                ),
                end_regex=_re.compile(rf"<!--/{_globals.UUID}-->", flags=_re.NOFLAG),
                start=f'<!--{_globals.UUID} generate section="{{section}}"-->',
                stop=f"<!--/{_globals.UUID}-->",
                data=lambda match: match[2],
            ),
        }
    )

    path: _anyio.Path
    section: str

    @classmethod
    async def find(cls, path: _anyio.Path) -> _typing.Collection[str]:
        return (await _FILE_SECTION_CACHE[path]).sections.keys()

    @_contextlib.asynccontextmanager
    async def open(self):
        async with (
            _FileSectionIO(self)
            if self.section
            else await _anyio.open_file(self.path, mode="r+t", **_globals.OPEN_OPTIONS)
        ) as file:
            yield file


@_typing.final
@_dataclasses.dataclass(
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
    EMPTY: _typing.ClassVar[_typing.Self]
    mod_time: int
    sections: _typing.Mapping[str, tuple[slice, str]]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "sections", _types.MappingProxyType(dict(self.sections))
        )


_FileSectionCacheData.EMPTY = _FileSectionCacheData(mod_time=-1, sections={})


class _FileSectionCache(dict[_anyio.Path, _typing.Awaitable[_FileSectionCacheData]]):
    __slots__: _typing.ClassVar = ("__locks",)

    def __init__(self) -> None:
        super().__init__()
        self.__locks = _weakref.WeakKeyDictionary[
            _anyio.Path, _typing.Callable[[], _threading.Lock]
        ]()

    async def __getitem__(self, key: _anyio.Path):
        key = await key.resolve(strict=True)
        _, ext = _os.path.splitext(key)
        try:
            format = FileSection.SECTION_FORMATS[ext]
        except KeyError as ex:
            raise ValueError(f"Unknown extension: {key}") from ex
        async with _util.async_lock(
            self.__locks.setdefault(key, _functools.cache(_threading.Lock))()
        ):
            try:
                cache = await super().__getitem__(key)
            except KeyError:
                cache = _FileSectionCacheData.EMPTY
            try:
                mod_time = (await _asyncstdlib.sync(_os.stat)(key)).st_mtime_ns
                if mod_time != cache.mod_time:
                    async with await _anyio.open_file(
                        key, mode="rt", **_globals.OPEN_OPTIONS
                    ) as file:
                        text = await file.read()
                    sections = dict[str, tuple[slice, str]]()
                    read_to: int = 0
                    start: _re.Match[str]
                    for start in format.start_regex.finditer(text):
                        start_idx = start.start()
                        if start.start() < read_to:
                            raise ValueError(
                                f"Overlapping section at char {start.start()}: {key}"
                            )
                        section = format.data(start)
                        if section in sections:
                            raise ValueError(f'Duplicated section "{section}": {key}')
                        end_str: str = format.stop.format(section=section)
                        try:
                            end_idx: int = text.index(end_str, start.end())
                        except ValueError as ex:
                            raise ValueError(
                                f"Unenclosure from char {start.start()}: {key}"
                            ) from ex
                        slice0 = slice(start_idx + len(start[0]), end_idx)
                        sections[section] = (slice0, text[slice0])
                        read_to = end_idx + len(end_str)
                    end: _re.Match[str]
                    for end in _itertools.islice(
                        format.end_regex.finditer(text), len(sections), None
                    ):
                        raise ValueError(
                            f"Too many closings at char {end.start()}: {key}"
                        )
                    cache = _FileSectionCacheData(
                        mod_time=mod_time,
                        sections=sections,
                    )
            finally:
                super().__setitem__(key, _util.wrap_async(cache))  # Replenish awaitable
        return cache

    def __setitem__(
        self,
        key: _anyio.Path,
        value: _typing.Awaitable[_FileSectionCacheData],
    ):
        raise TypeError("Unsupported")


_FILE_SECTION_CACHE = _FileSectionCache()


@_typing.final
class _FileSectionIO(_io.StringIO):
    __slots__: _typing.ClassVar = ("__closure", "__file", "__slice", "__initial_value")

    def __init__(self, closure: FileSection, /):
        self.__closure = closure

    def __enter__(self):
        raise TypeError("Unsupported")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _types.TracebackType | None,
    ):
        raise TypeError("Unsupported")

    def close(self):
        raise TypeError("Unsupported")

    async def aclose(self):
        try:
            try:
                self.seek(0)
                data = self.read()
                if data == self.__initial_value:
                    return
                await self.__file.seek(0)
                text = await self.__file.read()
                async with _asyncio.TaskGroup() as group:
                    group.create_task(self.__file.seek(0))
                    write = (
                        f"{text[: self.__slice.start]}{data}{text[self.__slice.stop :]}"
                    )
                await self.__file.write(write)
                await self.__file.truncate()
            finally:
                await self.__file.aclose()
        finally:
            super().close()

    async def __aenter__(self):
        self.__file = await _anyio.open_file(
            self.__closure.path, mode="r+t", **_globals.OPEN_OPTIONS
        )
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
        traceback: _types.TracebackType | None,
    ):
        await self.aclose()


Location.register(FileSection)
assert issubclass(FileSection, Location)


@_typing.final
@_dataclasses.dataclass(
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
    location: Location
    text: str

    @classmethod
    def isinstance(cls, any: _typing.Any) -> _typing.TypeGuard[_typing.Self]:
        try:
            return isinstance(any.location, Location) and isinstance(any.text, str)
        except AttributeError:
            return False
