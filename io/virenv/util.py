# -*- coding: UTF-8 -*-
from ... import (
    FLASHCARD_STATES_FORMAT as _FC_ST_FMT,
    FLASHCARD_STATES_REGEX as _FC_ST_RE,
)
from ...util import *  # Intentional wildcard
from ..util import *  # Intentional wildcard
from .config import CONFIG as _CFG, FlashcardSeparatorType as _FcSepT
import abc as _abc
import dataclasses as _dataclasses
import datetime as _datetime
import re as _re
import types as _types
import typing as _typing


def export_seq(*seq: _typing.Callable[..., _typing.Any] | type):
    return _types.MappingProxyType({val.__name__: val for val in seq})


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
    FORMAT: _typing.ClassVar = _FC_ST_FMT
    REGEX: _typing.ClassVar = _FC_ST_RE

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
