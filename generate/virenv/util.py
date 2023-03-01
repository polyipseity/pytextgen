# -*- coding: UTF-8 -*-
import abc as _abc
import dataclasses as _dataclasses
import datetime as _datetime
import threading as _threading
import io as _io
import itertools as _itertools
import os as _os
import pathlib as _pathlib
import re as _re
import types as _types
import typing as _typing

from ... import globals as _globals
from ...util import *


class Location(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_abc.abstractmethod
    def open(self) -> _typing.TextIO:
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
    path: _pathlib.Path

    def open(self) -> _typing.TextIO:
        return open(self.path, mode="r+t", **_globals.open_options)

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", self.path.resolve(strict=True))


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

    section_formats: _typing.ClassVar[
        _typing.Mapping[str, SectionFormat]
    ] = _types.MappingProxyType(
        {
            "": SectionFormat(
                start_regex=_re.compile(
                    rf"\[{_globals.uuid},generate,([^,\]]*)\]", flags=_re.NOFLAG
                ),
                end_regex=_re.compile(rf"\[{_globals.uuid},end\]", flags=_re.NOFLAG),
                start=f"[{_globals.uuid},generate,{{section}}]",
                stop=f"[{_globals.uuid},end]",
            ),
            ".md": SectionFormat(
                start_regex=_re.compile(
                    rf'<!--{_globals.uuid} generate section="([^"]*)"-->',
                    flags=_re.NOFLAG,
                ),
                end_regex=_re.compile(rf"<!--/{_globals.uuid}-->", flags=_re.NOFLAG),
                start=f'<!--{_globals.uuid} generate section="{{section}}"-->',
                stop=f"<!--/{_globals.uuid}-->",
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
        empty: _typing.ClassVar[_typing.Self]
        mod_time: int
        sections: _typing.AbstractSet[str]

        def __post_init__(self) -> None:
            object.__setattr__(self, "sections", frozenset(self.sections))

    __CacheData.empty = __CacheData(mod_time=-1, sections=frozenset())

    class __ValidateCache(dict[_pathlib.Path, __CacheData]):
        __slots__: _typing.ClassVar = ("__lock",)
        __ValueType: _typing.ClassVar[type["FileSection.__CacheData"]]

        def __init_subclass__(
            cls,
            value_type: type["FileSection.__CacheData"],
            **kwargs: _typing.Any | None,
        ) -> None:
            super().__init_subclass__(**kwargs)
            cls.__ValueType = value_type

        def __init__(self) -> None:
            super().__init__()
            self.__lock: _threading.Lock = _threading.Lock()

        def __getitem__(self, key: _pathlib.Path) -> "FileSection.__CacheData":
            ext: str
            _, ext = _os.path.splitext(key)
            try:
                format: FileSection.SectionFormat = FileSection.section_formats[ext]
            except KeyError as ex:
                raise ValueError(f"Unknown extension: {key}") from ex
            mod_time: int = _os.stat(key).st_mtime_ns
            with self.__lock:
                try:
                    cache: FileSection.__CacheData = super().__getitem__(key)
                except KeyError:
                    cache = self.__ValueType.empty
                if mod_time != cache.mod_time:
                    text: str
                    file: _typing.TextIO
                    with open(key, mode="rt", **_globals.open_options) as file:
                        text = file.read()
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
                    cache = self.__ValueType(
                        mod_time=mod_time,
                        sections=sections,
                    )
                    super().__setitem__(key, cache)
            return cache

        def __setitem__(
            self, key: _pathlib.Path, value: "FileSection.__CacheData"
        ) -> None:
            raise TypeError(f"Unsupported")

    __ValidateCache = type(
        "__ValidateCache", (__ValidateCache,), {}, value_type=__CacheData
    )
    __validate_cache: _typing.ClassVar[__ValidateCache] = __ValidateCache()

    path: _pathlib.Path
    section: str

    def open(self) -> _typing.TextIO:
        if self.section:

            @_typing.final
            class IO(_io.StringIO):
                __slots__: _typing.ClassVar = ("__file", "__slice")

                def __init__(self, closure: FileSection, /) -> None:
                    ext: str
                    _, ext = _os.path.splitext(closure.path)
                    start_format: str = closure.section_formats[ext].start.format(
                        section=closure.section
                    )
                    stop_format: str = closure.section_formats[ext].stop.format(
                        section=closure.section
                    )
                    self.__file: _typing.TextIO = open(
                        closure.path, mode="r+t", **_globals.open_options
                    )
                    try:
                        text: str = self.__file.read()
                        start: int = text.find(start_format)
                        if start == -1:
                            raise ValueError(f"Not found: {closure}")
                        start += len(start_format)
                        stop: int = text.find(stop_format, start)
                        if stop == -1:
                            raise ValueError(
                                f"Unenclosure from char {start}: {closure}"
                            )
                        self.__slice: slice = slice(start, stop)
                        super().__init__(text[self.__slice])
                    except Exception as ex:
                        self.__file.close()
                        raise ex

                def close(self) -> None:
                    try:
                        self.seek(0)
                        data: str = self.read()
                        with self.__file:
                            self.__file.seek(0)
                            text: str = self.__file.read()
                            self.__file.seek(0)
                            self.__file.write(
                                "".join(
                                    (
                                        text[: self.__slice.start],
                                        data,
                                        text[self.__slice.stop :],
                                    )
                                )
                            )
                            self.__file.truncate()
                    finally:
                        super().close()

            return IO(self)
        return open(self.path, mode="r+t", **_globals.open_options)

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", self.path.resolve(strict=True))
        if (
            not self.section
            or self.section not in self.__validate_cache[self.path].sections
        ):
            raise ValueError(f"Section not found: {self}")


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
    class SeparatorKey:
        reversible: bool
        multiline: bool

    separators: _typing.ClassVar[
        _typing.Mapping[SeparatorKey, str]
    ] = _types.MappingProxyType(
        {
            SeparatorKey(reversible=False, multiline=False): "::",
            SeparatorKey(reversible=True, multiline=False): ":::",
            SeparatorKey(reversible=False, multiline=True): "\n??\n",
            SeparatorKey(reversible=True, multiline=True): "\n???\n",
        }
    )

    left: str
    right: str
    _: _dataclasses.KW_ONLY
    reversible: bool

    def __str__(self) -> str:
        return self.separators[
            self.SeparatorKey(
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
    token: tuple[str, str] = ("{{", "}}")
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
    format: _typing.ClassVar[str] = "!{date},{interval},{ease}"
    regex: _typing.ClassVar[_re.Pattern[str]] = _re.compile(
        r"!(\d{4}-\d{2}-\d{2}),(\d+),(\d+)", flags=_re.NOFLAG
    )

    date: _datetime.date
    interval: int
    ease: int

    def __str__(self) -> str:
        return self.format.format(
            date=self.date, interval=self.interval, ease=self.ease
        )

    @classmethod
    def compile_many(cls, text: str) -> _typing.Iterator[_typing.Self]:
        match: _re.Match[str]
        for match in cls.regex.finditer(text):
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
    format: _typing.ClassVar[str] = _globals.flashcard_states_format
    regex: _typing.ClassVar[_re.Pattern[str]] = _globals.flashcard_states_regex

    def __str__(self) -> str:
        if self:
            return self.format.format(states="".join(map(str, self)))
        return ""

    @classmethod
    def compile_many(cls, text: str) -> _typing.Iterator[_typing.Self]:
        match: _re.Match[str]
        for match in cls.regex.finditer(text):
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
