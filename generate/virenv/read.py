# -*- coding: UTF-8 -*-
from .util import (
    FlashcardStateGroup as _FcStGrp,
    Location as _Loc,
    maybe_async as _masync,
)


async def read_flashcard_states(source: str | _Loc):
    if isinstance(source, _Loc):
        async with source.open() as io:
            source = await _masync(io.read())
    return _FcStGrp.compile_many(source)
