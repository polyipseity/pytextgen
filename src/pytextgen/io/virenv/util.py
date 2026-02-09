"""Utility helpers for the virtual environment IO layer."""

from abc import ABCMeta as _ABCM
from abc import abstractmethod as _amethod
from dataclasses import KW_ONLY as _KW_ONLY
from dataclasses import dataclass as _dc
from dataclasses import field as _field
from datetime import date as _date
from re import (
    NOFLAG as _NOFLAG,
)
from re import (
    Pattern as _Pattern,
)
from re import (
    compile as _re_comp,
)
from re import (
    escape as _re_esc,
)
from typing import (
    Any as _Any,
)
from typing import (
    Callable as _Call,
)
from typing import (
    ClassVar as _ClsVar,
)
from typing import (
    Sequence as _Seq,
)
from typing import (
    final as _fin,
)

from ... import (
    FLASHCARD_STATES_FORMAT as _FC_ST_FMT,
)
from ... import (
    FLASHCARD_STATES_REGEX as _FC_ST_RE,
)
from ...util import (  # explicit imports (avoid star-imports)
    IteratorSequence,
    TypedTuple,
    Unit,
    abc_subclasshook_check,
    affix_lines,
    constant,
    identity,
    ignore_args,
    split_by_punctuations,
    strip_lines,
    wrap_async,
)

# from ..util import *  # intentionally removed star-import; no names from ..util are required here
from .config import CONFIG as _CFG
from .config import FlashcardSeparatorType as _FcSepT

__all__ = (
    "export_seq",
    "FlashcardGroup",
    "TwoSidedFlashcard",
    "ClozeFlashcardGroup",
    "FlashcardState",
    "FlashcardStateGroup",
    "StatefulFlashcardGroup",
    "IteratorSequence",
    "Unit",
    "affix_lines",
    "strip_lines",
    "wrap_async",
    "constant",
    "identity",
    "ignore_args",
    "split_by_punctuations",
)


def export_seq(*seq: _Call[..., _Any] | type):
    """Utility returning a mapping of names to callables/types for exports."""
    return {val.__name__: val for val in seq}


class FlashcardGroup(_Seq[str], metaclass=_ABCM):
    """Abstract sequence-like representing a flashcard.

    Concrete implementations must implement `__str__` to render the
    flashcard as text.
    """

    __slots__: _ClsVar = ()

    @_amethod
    def __str__(self) -> str:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        return abc_subclasshook_check(
            FlashcardGroup, cls, subclass, names=(cls.__str__.__name__,)
        )


@_fin
@FlashcardGroup.register
@_dc(
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
    """A two-sided flashcard with optional reversibility."""

    left: str
    right: str
    _: _KW_ONLY
    reversible: bool

    def __str__(self):
        return _CFG.flashcard_separators[
            _FcSepT(
                reversible=self.reversible,
                multiline="\n" in self.left or "\n" in self.right,
            )
        ].join((self.left, self.right))

    def __len__(self):
        return 2 if self.reversible else 1

    def __getitem__(self, index: int):
        if self.reversible:
            if -2 > index or index >= 2:
                raise IndexError(index)
        elif -1 > index or index >= 1:
            raise IndexError(index)
        return str(self)


assert issubclass(TwoSidedFlashcard, FlashcardGroup)


@_fin
@FlashcardGroup.register
@_dc(
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
    """Represents a cloze-style flashcard group extracted from text.

    Finds tokens in `context` delimited by `token` and exposes them
    via sequence protocol.
    """

    __pattern_cache: _ClsVar = dict[tuple[str, str], _Pattern[str]]()

    context: str
    _: _KW_ONLY
    token: tuple[str, str] = _CFG.cloze_token
    _clozes: _Seq[str] = _field(init=False, repr=False, hash=False, compare=False)

    def __post_init__(self):
        try:
            pattern = self.__pattern_cache[self.token]
        except KeyError:
            e_token = (_re_esc(self.token[0]), _re_esc(self.token[1]))
            self.__pattern_cache[self.token] = pattern = _re_comp(
                rf"{e_token[0]}((?:(?!{e_token[1]}).)+){e_token[1]}", _NOFLAG
            )
        object.__setattr__(
            self, "_clozes", tuple(match[1] for match in pattern.finditer(self.context))
        )

    def __str__(self):
        return self.context

    def __len__(self):
        return len(self._clozes)

    def __getitem__(self, index: int):
        return self._clozes[index]


assert issubclass(ClozeFlashcardGroup, FlashcardGroup)


@_fin
@_dc(
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
    """Represents a single flashcard state entry (date, interval, ease)."""

    FORMAT: _ClsVar = "!{date},{interval},{ease}"
    REGEX: _ClsVar = _re_comp(r"!(\d{4}-\d{2}-\d{2}),(\d+),(\d+)", _NOFLAG)

    date: _date
    interval: int
    ease: int

    def __str__(self):
        return self.FORMAT.format(
            date=self.date, interval=self.interval, ease=self.ease
        )

    @classmethod
    def compile_many(cls, text: str):
        for match in cls.REGEX.finditer(text):
            yield cls(
                date=_date.fromisoformat(match[1]),
                interval=int(match[2]),
                ease=int(match[3]),
            )

    @classmethod
    def compile(cls, text: str):
        rets = cls.compile_many(text)
        try:
            ret = next(rets)
        except StopIteration as ex:
            raise ValueError(f"No matches: {text}") from ex
        try:
            next(rets)
            raise ValueError(f"Too many matches: {text}")
        except StopIteration:
            pass
        return ret


@_fin
class FlashcardStateGroup(TypedTuple[FlashcardState], element_type=FlashcardState):
    """A group of `FlashcardState` objects serialized as a single section."""

    __slots__: _ClsVar = ()
    FORMAT: _ClsVar = _FC_ST_FMT
    REGEX: _ClsVar = _FC_ST_RE

    def __str__(self):
        if self:
            return self.FORMAT.format(states="".join(map(str, self)))
        return ""

    @classmethod
    def compile_many(cls, text: str):
        for match in cls.REGEX.finditer(text):
            yield cls(FlashcardState.compile_many(text[match.start() : match.end()]))

    @classmethod
    def compile(cls, text: str):
        rets = cls.compile_many(text)
        try:
            ret = next(rets)
        except StopIteration as ex:
            raise ValueError(f"No matches: {text}") from ex
        try:
            next(rets)
            raise ValueError(f"Too many matches: {text}")
        except StopIteration:
            pass
        return ret


@_fin
@_dc(
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
    """Pairing of a `FlashcardGroup` and its `FlashcardStateGroup` state."""

    flashcard: FlashcardGroup
    state: FlashcardStateGroup

    def __str__(self):
        return " ".join((str(self.flashcard), str(self.state)))
