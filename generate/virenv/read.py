# -*- coding: UTF-8 -*-
from .util import FlashcardStateGroup, Location, maybe_async


async def read_flashcard_states(source: str | Location):
    if isinstance(source, Location):
        async with source.open() as io:
            source = await maybe_async(io.read())
    return FlashcardStateGroup.compile_many(source)
