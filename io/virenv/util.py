# -*- coding: UTF-8 -*-
import abc as _abc
import asyncio as _asyncio
import anyio as _anyio
import contextlib as _contextlib
import dataclasses as _dataclasses
import datetime as _datetime
import functools as _functools
import threading as _threading
import io as _io
import itertools as _itertools
import os as _os
import re as _re
import types as _types
import typing as _typing
import weakref as _weakref

from ... import globals as _globals
from ...util import *  # Intentional wildcard import
from .config import CONFIG as _CFG, FlashcardSeparatorType as _FcSepT


class Location(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_abc.abstractmethod
    def open(
        self,
    ) -> _contextlib.AbstractAsyncContextManager[
        _typing.TextIO | _anyio.AsyncFile[str]
    ]:
        raise NotImplementedError(self)

    @property
    @_abc.abstractmethod
    def path(self) -> _anyio.Path | None:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return abc_subclasshook_check(
            Location,
            cls,
            subclass,
            names=(
                "path",
                cls.open.__name__,
            ),
        )


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

    SECTION_FORMATS: _typing.ClassVar[
        _typing.Mapping[str, SectionFormat]
    ] = _types.MappingProxyType(
        {
            "": SectionFormat(
                start_regex=_re.compile(
                    rf"\[{_globals.UUID},generate,([^,\]]*)\]", flags=_re.NOFLAG
                ),
                end_regex=_re.compile(rf"\[{_globals.UUID},end\]", flags=_re.NOFLAG),
                start=f"[{_globals.UUID},generate,{{section}}]",
                stop=f"[{_globals.UUID},end]",
            ),
            ".md": SectionFormat(
                start_regex=_re.compile(
                    rf'<!--{_globals.UUID} generate section="([^"]*)"-->',
                    flags=_re.NOFLAG,
                ),
                end_regex=_re.compile(rf"<!--/{_globals.UUID}-->", flags=_re.NOFLAG),
                start=f'<!--{_globals.UUID} generate section="{{section}}"-->',
                stop=f"<!--/{_globals.UUID}-->",
            ),
        }
    )

    path: _anyio.Path
    section: str

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
    sections: _typing.Mapping[str, slice]

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
        mod_time = (await asyncify(_os.stat)(key)).st_mtime_ns
        async with async_lock(
            self.__locks.setdefault(key, _functools.cache(_threading.Lock))()
        ):
            try:
                cache = await super().__getitem__(key)
            except KeyError:
                cache = _FileSectionCacheData.EMPTY
            try:
                if mod_time != cache.mod_time:
                    async with await _anyio.open_file(
                        key, mode="rt", **_globals.OPEN_OPTIONS
                    ) as file:
                        text = await file.read()
                    sections = dict[str, slice]()
                    read_to: int = 0
                    start: _re.Match[str]
                    for start in format.start_regex.finditer(text):
                        start_idx = start.start()
                        if start.start() < read_to:
                            raise ValueError(
                                f"Overlapping section at char {start.start()}: {key}"
                            )
                        section: str = text[start.start(1) : start.end(1)]
                        if section in sections:
                            raise ValueError(f'Duplicated section "{section}": {key}')
                        end_str: str = format.stop.format(section=section)
                        try:
                            end_idx: int = text.index(end_str, start.end())
                        except ValueError as ex:
                            raise ValueError(
                                f"Unenclosure from char {start.start()}: {key}"
                            ) from ex
                        sections[section] = slice(start_idx + len(start[0]), end_idx)
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
                super().__setitem__(key, async_value(cache))  # Replenish awaitable
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
    __slots__: _typing.ClassVar = ("__closure", "__file", "__slice")

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

    async def __aenter__(self):
        self.__file = await _anyio.open_file(
            self.__closure.path, mode="r+t", **_globals.OPEN_OPTIONS
        )
        try:
            self.__slice = (await _FILE_SECTION_CACHE[self.__closure.path]).sections[
                self.__closure.section
            ]
            super().__init__((await self.__file.read())[self.__slice])
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
        try:
            try:
                async with _asyncio.TaskGroup() as group:

                    async def read():
                        await self.__file.seek(0)
                        return await self.__file.read()

                    text = group.create_task(read())
                    self.seek(0)
                    data = self.read()
                text = await text
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


Location.register(FileSection)
assert issubclass(FileSection, Location)


class FlashcardGroup(_typing.Sequence[str], metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_abc.abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return abc_subclasshook_check(
            FlashcardGroup, cls, subclass, names=(cls.__str__.__name__,)
        )


@_typing.final
@_dataclasses.dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=False,
    slots=True,
)
class TwoSidedFlashcard:
    left: str
    right: str
    _: _dataclasses.KW_ONLY
    reversible: bool

    def __str__(self) -> str:
        return _CFG.flashcard_separators[
            _FcSepT(
                reversible=self.reversible,
                multiline="\n" in self.left or "\n" in self.right,
            )
        ].join((self.left, self.right))

    def __len__(self) -> int:
        return 2 if self.reversible else 1

    def __getitem__(self, index: int) -> str:
        if self.reversible:
            if -2 > index or index >= 2:
                raise IndexError(index)
        elif -1 > index or index >= 1:
            raise IndexError(index)
        return str(self)


FlashcardGroup.register(TwoSidedFlashcard)
assert issubclass(TwoSidedFlashcard, FlashcardGroup)


@_dataclasses.dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=False,
    slots=True,
)
class ClozeFlashcardGroup:
    __pattern_cache: _typing.ClassVar[
        _typing.MutableMapping[tuple[str, str], _re.Pattern[str]]
    ] = {}

    context: str
    _: _dataclasses.KW_ONLY
    token: tuple[str, str] = _CFG.cloze_token
    _clozes: _typing.Sequence[str] = _dataclasses.field(
        init=False, repr=False, hash=False, compare=False
    )

    def __post_init__(self) -> None:
        try:
            pattern: _re.Pattern[str] = self.__pattern_cache[self.token]
        except KeyError:
            e_token: tuple[str, str] = (
                _re.escape(self.token[0]),
                _re.escape(self.token[1]),
            )
            self.__pattern_cache[self.token] = pattern = _re.compile(
                rf"{e_token[0]}((?:(?!{e_token[1]}).)+){e_token[1]}",
                flags=_re.NOFLAG,
            )
        object.__setattr__(
            self, "_clozes", tuple(match[1] for match in pattern.finditer(self.context))
        )

    def __str__(self) -> str:
        return self.context

    def __len__(self) -> int:
        return len(self._clozes)

    def __getitem__(self, index: int) -> str:
        return self._clozes[index]


FlashcardGroup.register(ClozeFlashcardGroup)
assert issubclass(ClozeFlashcardGroup, FlashcardGroup)


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
class FlashcardState:
    FORMAT: _typing.ClassVar = "!{date},{interval},{ease}"
    REGEX: _typing.ClassVar = _re.compile(
        r"!(\d{4}-\d{2}-\d{2}),(\d+),(\d+)", flags=_re.NOFLAG
    )

    date: _datetime.date
    interval: int
    ease: int

    def __str__(self) -> str:
        return self.FORMAT.format(
            date=self.date, interval=self.interval, ease=self.ease
        )

    @classmethod
    def compile_many(cls, text: str) -> _typing.Iterator[_typing.Self]:
        match: _re.Match[str]
        for match in cls.REGEX.finditer(text):
            yield cls(
                date=_datetime.date.fromisoformat(match[1]),
                interval=int(match[2]),
                ease=int(match[3]),
            )

    @classmethod
    def compile(cls, text: str) -> _typing.Self:
        rets: _typing.Iterator[_typing.Self] = cls.compile_many(text)
        try:
            ret: _typing.Self = next(rets)
        except StopIteration as ex:
            raise ValueError(f"No matches: {text}") from ex
        try:
            next(rets)
            raise ValueError(f"Too many matches: {text}")
        except StopIteration:
            pass
        return ret


@_typing.final
class FlashcardStateGroup(TypedTuple[FlashcardState], element_type=FlashcardState):
    __slots__: _typing.ClassVar = ()
    FORMAT: _typing.ClassVar = _globals.FLASHCARD_STATES_FORMAT
    REGEX: _typing.ClassVar = _globals.FLASHCARD_STATES_REGEX

    def __str__(self) -> str:
        if self:
            return self.FORMAT.format(states="".join(map(str, self)))
        return ""

    @classmethod
    def compile_many(cls, text: str) -> _typing.Iterator[_typing.Self]:
        match: _re.Match[str]
        for match in cls.REGEX.finditer(text):
            yield cls(FlashcardState.compile_many(text[match.start() : match.end()]))

    @classmethod
    def compile(cls, text: str) -> _typing.Self:
        rets: _typing.Iterator[_typing.Self] = cls.compile_many(text)
        try:
            ret: _typing.Self = next(rets)
        except StopIteration as ex:
            raise ValueError(f"No matches: {text}") from ex
        try:
            next(rets)
            raise ValueError(f"Too many matches: {text}")
        except StopIteration:
            pass
        return ret


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
class StatefulFlashcardGroup:
    flashcard: FlashcardGroup
    state: FlashcardStateGroup

    def __str__(self) -> str:
        return " ".join((str(self.flashcard), str(self.state)))
