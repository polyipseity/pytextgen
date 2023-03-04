# -*- coding: UTF-8 -*-
from ... import io as _io
from .util import (
    FlashcardStateGroup as _FcStGrp,
    maybe_async as _masync,
)


async def read_flashcard_states(source: str | _io.Location):
    if isinstance(source, _io.Location):
        async with source.open() as io:
            source = await _masync(io.read())
    return _FcStGrp.compile_many(source)
