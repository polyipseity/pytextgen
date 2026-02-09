"""Options and enum types used by I/O operations.

Defines `ClearType`, `ClearOpts`, and `GenOpts` dataclasses used to
control behaviour of the `clear` and `generate` pipelines.
"""

from dataclasses import dataclass as _dc
from enum import StrEnum as _StrEnum
from enum import unique as _unq
from typing import AbstractSet as _ASet
from typing import final as _fin

from ..util import Compiler as _Compiler

__all__ = ("ClearType", "ClearOpts", "GenOpts")


@_fin
@_unq
class ClearType(_StrEnum):
    """Types of data that can be cleared from inputs.

    - CONTENT: remove generated content blocks
    - FLASHCARD_STATE: remove flashcard state metadata
    """

    CONTENT = "content"
    FLASHCARD_STATE = "fc_state"


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
    """Options for clearing operations.

    Attributes:
        types: a set of `ClearType` values selecting what to clear.
    """

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
    """Generation options passed to readers/writers.

    Attributes:
        timestamp: whether to write/update generation timestamps.
        init_flashcards: whether flashcards should be initialized.
        compiler: callable used to compile extracted code blocks.
    """

    timestamp: bool
    init_flashcards: bool
    compiler: _Compiler
