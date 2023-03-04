# -*- coding: UTF-8 -*-
import abc as _abc
import aiofiles as _aiofiles
import aiofiles.threadpool.text as _aiofiles_threadpool_text
import anyio as _anyio
import contextlib as _contextlib
import dataclasses as _dataclasses
import datetime as _datetime
import threading as _threading
import io as _io
import itertools as _itertools
import os as _os
import re as _re
import types as _types
import typing as _typing

from ... import globals as _globals
from ...util import *  # Intentional wildcard import
from .config import CONFIG as _CFG, FlashcardSeparatorType as _FcSepT


class Location(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_abc.abstractmethod
    def open(
        self,
    ) -> _contextlib.AbstractAsyncContextManager[
        _typing.TextIO | _aiofiles_threadpool_text.AsyncTextIOWrapper
    ]:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return abc_subclasshook_check(
            Location, cls, subclass, names=(cls.open.__name__,)
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
        async with _aiofiles.open(
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
    class __CacheData:
        EMPTY: _typing.ClassVar[_typing.Self]
        mod_time: int
        sections: _typing.AbstractSet[str]

        def __post_init__(self) -> None:
            object.__setattr__(self, "sections", frozenset(self.sections))

    __CacheData.EMPTY = __CacheData(mod_time=-1, sections=frozenset())

    class __ValidateCache(dict[_anyio.Path, _typing.Awaitable[__CacheData]]):
        __slots__: _typing.ClassVar = ("__lock",)
        __VALUE_TYPE: _typing.ClassVar

        def __init_subclass__(
            cls,
            value_type: type["FileSection.__CacheData"],
            **kwargs: _typing.Any,
        ) -> None:
            super().__init_subclass__(**kwargs)
            cls.__VALUE_TYPE = value_type

        def __init__(self) -> None:
            super().__init__()
            self.__lock: _threading.Lock = _threading.Lock()

        async def __getitem__(self, key: _anyio.Path):
            _, ext = _os.path.splitext(key)
            try:
                format = FileSection.SECTION_FORMATS[ext]
            except KeyError as ex:
                raise ValueError(f"Unknown extension: {key}") from ex
            mod_time = (await asyncify(_os.stat)(key)).st_mtime_ns
            async with async_lock(self.__lock):
                try:
                    cache = await super().__getitem__(key)
                except KeyError:
                    cache = self.__VALUE_TYPE.EMPTY
                if mod_time != cache.mod_time:
                    async with _aiofiles.open(
                        key, mode="rt", **_globals.OPEN_OPTIONS
                    ) as file:
                        text = await file.read()
                    sections: _typing.MutableSet[str] = set()
                    read_to: int = 0
                    start: _re.Match[str]
                    for start in format.start_regex.finditer(text):
                        if start.start() < read_to:
                            raise ValueError(
                                f"Overlapping section at char {start.start()}: {key}"
                            )
                        section: str = text[start.start(1) : start.end(1)]
                        if section in sections:
                            raise ValueError(f'Duplicated section "{section}": {key}')
                        sections.add(section)
                        end_str: str = format.stop.format(section=section)
                        try:
                            end_idx: int = text.index(end_str, start.end())
                        except ValueError as ex:
                            raise ValueError(
                                f"Unenclosure from char {start.start()}: {key}"
                            ) from ex
                        read_to = end_idx + len(end_str)
                    end: _re.Match[str]
                    for end in _itertools.islice(
                        format.end_regex.finditer(text), len(sections), None
                    ):
                        raise ValueError(
                            f"Too many closings at char {end.start()}: {key}"
                        )
                    cache = self.__VALUE_TYPE(
                        mod_time=mod_time,
                        sections=sections,
                    )
                super().__setitem__(key, async_value(cache))
            return cache

        def __setitem__(
            self,
            key: _anyio.Path,
            value: "_typing.Awaitable[FileSection.__CacheData]",
        ):
            raise TypeError("Unsupported")

    __ValidateCache = type(
        "__ValidateCache", (__ValidateCache,), {}, value_type=__CacheData
    )
    __VALIDATE_CACHE: _typing.ClassVar = __ValidateCache()

    path: _anyio.Path
    section: str

    @_contextlib.asynccontextmanager
    async def open(self):
        if self.section not in (await self.__VALIDATE_CACHE[self.path]).sections:
            raise ValueError(f"Section not found: {self}")
        async with (
            _FileSectionIO(self)
            if self.section
            else _aiofiles.open(self.path, mode="r+t", **_globals.OPEN_OPTIONS)
        ) as file:
            yield file


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
        _, ext = _os.path.splitext(self.__closure.path)
        start_format: str = self.__closure.SECTION_FORMATS[ext].start.format(
            section=self.__closure.section
        )
        stop_format: str = self.__closure.SECTION_FORMATS[ext].stop.format(
            section=self.__closure.section
        )
        self.__file = await _aiofiles.open(
            self.__closure.path, mode="r+t", **_globals.OPEN_OPTIONS
        ).__aenter__()
        try:
            text = await self.__file.read()
            start: int = text.find(start_format)
            if start == -1:
                raise ValueError(f"Not found: {self.__closure}")
            start += len(start_format)
            stop: int = text.find(stop_format, start)
            if stop == -1:
                raise ValueError(f"Unenclosure from char {start}: {self.__closure}")
            self.__slice = slice(start, stop)
            super().__init__(text[self.__slice])
            super().__enter__()
        except Exception as ex:
            await self.__file.close()
            raise ex
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _types.TracebackType | None,
    ):
        try:
            try:
                seek = self.__file.seek(0)
                self.seek(0)
                data: str = self.read()
                await seek
                text = await self.__file.read()
                seek1 = self.__file.seek(0)
                write = "".join(
                    (
                        text[: self.__slice.start],
                        data,
                        text[self.__slice.stop :],
                    )
                )
                await seek1
                await self.__file.write(write)
                await self.__file.truncate()
            finally:
                await self.__file.close()
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
