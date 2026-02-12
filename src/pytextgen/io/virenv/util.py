"""Utility helpers for the virtual environment IO layer."""

import datetime
from abc import ABCMeta, abstractmethod
from dataclasses import KW_ONLY, dataclass, field
from datetime import date
from re import NOFLAG, Pattern, escape
from re import compile as re_compile
from typing import Any, Callable, ClassVar, Iterator, Sequence, final

from ...meta import FLASHCARD_STATES_FORMAT, FLASHCARD_STATES_REGEX
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
from .config import CONFIG, FlashcardSeparatorType

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


def export_seq(*seq: Callable[..., Any] | type) -> dict[str, Any]:
    """Return a mapping of symbol names to callables or types.

    Returns a dict suitable for populating export maps used by package
    `meta` modules or other small registries.
    """
    return {val.__name__: val for val in seq}


class FlashcardGroup(Sequence[str], metaclass=ABCMeta):
    """Abstract sequence-like representing a flashcard.

    Concrete implementations must implement `__str__` to render the
    flashcard as text.
    """

    __slots__: ClassVar = ()

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        return abc_subclasshook_check(
            FlashcardGroup, cls, subclass, names=(cls.__str__.__name__,)
        )


@final
@FlashcardGroup.register
@dataclass(
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
    _: KW_ONLY
    reversible: bool

    def __str__(self):
        return CONFIG.flashcard_separators[
            FlashcardSeparatorType(
                reversible=self.reversible,
                multiline="\n" in self.left or "\n" in self.right,
            )
        ].join((self.left, self.right))

    def __len__(self):
        return 2 if self.reversible else 1

    def __getitem__(self, index: int) -> str:
        if self.reversible:
            if -2 > index or index >= 2:
                raise IndexError(index)
        elif -1 > index or index >= 1:
            raise IndexError(index)
        return str(self)


assert issubclass(TwoSidedFlashcard, FlashcardGroup)


@final
@FlashcardGroup.register
@dataclass(
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

    __pattern_cache: ClassVar = dict[tuple[str, str], Pattern[str]]()

    context: str
    _: KW_ONLY
    token: tuple[str, str] = CONFIG.cloze_token
    _clozes: Sequence[str] = field(init=False, repr=False, hash=False, compare=False)

    def __post_init__(self):
        try:
            pattern = self.__pattern_cache[self.token]
        except KeyError:
            e_token = (escape(self.token[0]), escape(self.token[1]))
            self.__pattern_cache[self.token] = pattern = re_compile(
                rf"{e_token[0]}((?:(?!{e_token[1]}).)+){e_token[1]}", NOFLAG
            )
        object.__setattr__(
            self, "_clozes", tuple(match[1] for match in pattern.finditer(self.context))
        )

    def __str__(self):
        return self.context

    def __len__(self):
        return len(self._clozes)

    def __getitem__(self, index: int) -> str:
        return self._clozes[index]


assert issubclass(ClozeFlashcardGroup, FlashcardGroup)


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
class FlashcardState:
    """Represents a single flashcard state entry (date, interval, ease)."""

    FORMAT: ClassVar = "!{date},{interval},{ease}"
    REGEX: ClassVar = re_compile(r"!(\d{4}-\d{2}-\d{2}),(\d+),(\d+)", NOFLAG)

    date: datetime.date
    interval: int
    ease: int

    def __str__(self):
        return self.FORMAT.format(
            date=self.date, interval=self.interval, ease=self.ease
        )

    @classmethod
    def compile_many(cls, text: str) -> Iterator["FlashcardState"]:
        """Yield parsed `FlashcardState` objects found in `text`."""
        for match in cls.REGEX.finditer(text):
            yield cls(
                date=date.fromisoformat(match[1]),
                interval=int(match[2]),
                ease=int(match[3]),
            )

    @classmethod
    def compile(cls, text: str) -> "FlashcardState":
        """Parse a single `FlashcardState` from `text`.

        Raises `ValueError` if zero or multiple matches are present.
        """
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


@final
class FlashcardStateGroup(TypedTuple[FlashcardState], element_type=FlashcardState):
    """A group of `FlashcardState` objects serialized as a single section."""

    __slots__: ClassVar = ()
    FORMAT: ClassVar = FLASHCARD_STATES_FORMAT
    REGEX: ClassVar = FLASHCARD_STATES_REGEX

    def __str__(self):
        if self:
            return self.FORMAT.format(states="".join(map(str, self)))
        return ""

    @classmethod
    def compile_many(cls, text: str) -> Iterator["FlashcardStateGroup"]:
        """Yield parsed `FlashcardStateGroup` objects found in `text`."""
        for match in cls.REGEX.finditer(text):
            yield cls(FlashcardState.compile_many(text[match.start() : match.end()]))

    @classmethod
    def compile(cls, text: str) -> "FlashcardStateGroup":
        """Parse a single `FlashcardStateGroup` from `text`.

        Raises `ValueError` if zero or multiple matches are present.
        """
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
class StatefulFlashcardGroup:
    """Pairing of a `FlashcardGroup` and its `FlashcardStateGroup` state."""

    flashcard: FlashcardGroup
    state: FlashcardStateGroup

    def __str__(self):
        return " ".join((str(self.flashcard), str(self.state)))
