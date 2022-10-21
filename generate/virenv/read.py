import typing as _typing

from . import util as _util


@_typing.overload
def read_flashcard_states(text: str)\
    -> _typing.Iterator[_util.FlashcardStateGroup]: ...


@_typing.overload
def read_flashcard_states(text: _util.Location)\
    -> _typing.Iterator[_util.FlashcardStateGroup]: ...


def read_flashcard_states(text: str | _util.Location | _typing.Any)\
        -> _typing.Iterator[_util.FlashcardStateGroup]:
    text0: str
    if isinstance(text, str):
        text0 = text
    elif isinstance(text, _util.Location):
        io: _typing.TextIO
        with text.open() as io:
            text0 = io.read()
    else:
        raise TypeError(text)
    return _util.FlashcardStateGroup.compile_many(text0)
