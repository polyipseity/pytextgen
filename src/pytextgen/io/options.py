"""Options and enum types used by I/O operations.

Defines `ClearType`, `ClearOpts`, and `GenOpts` dataclasses used to
control behaviour of the `clear` and `generate` pipelines.
"""

from collections.abc import Set
from dataclasses import dataclass
from enum import StrEnum, unique
from typing import final

from ..utils import Compiler

__all__ = ("ClearType", "ClearOpts", "GenOpts")


@final
@unique
class ClearType(StrEnum):
    """Types of data that can be cleared from inputs.

    - CONTENT: remove generated content blocks
    - FLASHCARD_STATE: remove flashcard state metadata
    """

    CONTENT = "content"
    FLASHCARD_STATE = "fc_state"


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
class ClearOpts:
    """Options for clearing operations.

    Attributes:
        types: a set of `ClearType` values selecting what to clear.
    """

    types: Set[ClearType]

    def __post_init__(self):
        """Normalize `types` to a frozenset after dataclass initialization."""
        object.__setattr__(self, "types", frozenset(self.types))


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
class GenOpts:
    """Generation options passed to readers/writers.

    Attributes:
        timestamp: whether to write/update generation timestamps.
        init_flashcards: whether flashcards should be initialized.
        compiler: callable used to compile extracted code blocks.
    """

    timestamp: bool
    init_flashcards: bool
    compiler: Compiler
