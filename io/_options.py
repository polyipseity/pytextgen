# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import enum as _enum
import typing as _typing

from .. import util as _util


@_typing.final
@_enum.unique
class ClearType(_enum.StrEnum):
    CONTENT: _typing.ClassVar = "content"
    FLASHCARD_STATE: _typing.ClassVar = "fc_state"


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
class ClearOpts:
    types: _typing.AbstractSet[ClearType]

    def __post_init__(self):
        object.__setattr__(self, "types", frozenset(self.types))


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
class GenOpts:
    timestamp: bool
    init_flashcards: bool
    compiler: _util.Compiler
