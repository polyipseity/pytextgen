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
    if isinstance(source, _Loc):
        async with source.open() as io:
            source = await _wasync(io.read())
    return _FcStGrp.compile_many(source)
