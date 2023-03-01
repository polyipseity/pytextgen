# -*- coding: UTF-8 -*-
import typing as _typing
from .util import *


@_typing.overload
def read_flashcard_states(text: str) -> _typing.Iterator[FlashcardStateGroup]:
    ...


@_typing.overload
def read_flashcard_states(
    text: Location,
) -> _typing.Iterator[FlashcardStateGroup]:
    ...


def read_flashcard_states(
    text: str | Location | _typing.Any,
) -> _typing.Iterator[FlashcardStateGroup]:
    text0: str
    if isinstance(text, str):
        text0 = text
    elif isinstance(text, Location):
        io: _typing.TextIO
        with text.open() as io:
            text0 = io.read()
    else:
        raise TypeError(text)
    return FlashcardStateGroup.compile_many(text0)
