from dataclasses import dataclass as _dc
from enum import StrEnum as _StrEnum
from enum import unique as _unq
from typing import AbstractSet as _ASet
from typing import ClassVar as _ClsVar
from typing import final as _fin

from ..util import Compiler as _Compiler


@_fin
@_unq
class ClearType(_StrEnum):
    CONTENT: _ClsVar = "content"
    FLASHCARD_STATE: _ClsVar = "fc_state"


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
class ClearOpts:
    types: _ASet[ClearType]

    def __post_init__(self):
        object.__setattr__(self, "types", frozenset(self.types))


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
class GenOpts:
    timestamp: bool
    init_flashcards: bool
    compiler: _Compiler
