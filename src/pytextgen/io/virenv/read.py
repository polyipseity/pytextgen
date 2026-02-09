"""Helpers for reading flashcard state input for the virtual environment IO."""

from ..util import (
    Location as _Loc,
)
from .util import (
    FlashcardStateGroup as _FcStGrp,
)
from .util import (
    wrap_async as _wasync,
)

__all__ = ("read_flashcard_states",)


async def read_flashcard_states(source: str | _Loc):
    """Read and yield flashcard states from `source`.

    `source` may be a location or a string containing flashcard state text.
    Returns an iterator of `FlashcardStateGroup` instances.
    """
    if isinstance(source, _Loc):
        async with source.open() as io:
            source = await _wasync(io.read())
    return _FcStGrp.compile_many(source)
