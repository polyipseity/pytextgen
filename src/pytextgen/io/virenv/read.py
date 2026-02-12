"""Helpers for reading flashcard state input for the virtual environment IO."""

from ..util import Location
from .util import FlashcardStateGroup, wrap_async

__all__ = ("read_flashcard_states",)


async def read_flashcard_states(source: str | Location):
    """Read and yield flashcard states from `source`.

    `source` may be a location or a string containing flashcard state text.
    Returns an iterator of `FlashcardStateGroup` instances.
    """
    if isinstance(source, Location):
        async with source.open() as io:
            source = await wrap_async(io.read())
    return FlashcardStateGroup.compile_many(source)
