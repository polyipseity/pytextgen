import itertools as _itertools
import typing as _typing

from .. import util as _util
from . import misc as _misc


def attach_flashcard_states(flashcards: _typing.Iterable[_util.FlashcardGroup], /, *,
                            states: _typing.Iterable[_util.FlashcardStateGroup])\
        -> _typing.Iterator[_util.StatefulFlashcardGroup]:
    for fc, st in zip(flashcards, _itertools.chain(states, _itertools.repeat(_util.FlashcardStateGroup()))):
        yield _util.StatefulFlashcardGroup(flashcard=fc, state=st)


def listify_flashcards(flashcards: _typing.Iterable[_util.StatefulFlashcardGroup])\
        -> str:
    def ret_gen() -> _typing.Iterator[str]:
        newline: str = ''
        for index, flashcard in enumerate(flashcards):
            yield newline
            yield str(index + 1)
            yield '. '
            yield str(flashcard)
            newline = '\n'
    return ''.join(ret_gen())


def memorize_linked_seq(strs: _typing.Iterable[str], /, *,
                        reversible: bool = True,
                        hinter: _typing.Callable[[int, str], tuple[str, str]] = lambda idx, str_: ('→', '←'))\
        -> _typing.Iterator[_util.FlashcardGroup]:
    class HintedStr(_typing.NamedTuple):
        str_: str
        left: str
        right: str
    prev: HintedStr | None = None
    index: int
    str_: str
    for index, str_ in enumerate(strs):
        cur: HintedStr = HintedStr(str_, *hinter(index, str_))
        if prev is not None:
            yield _typing.cast(
                _util.FlashcardGroup,
                _util.TwoSidedFlashcard(
                    prev.str_ + cur.left, prev.right + cur.str_,
                    reversible=reversible,
                )
            )
        prev = cur


def semantics_seq_map(map: _typing.Iterable[tuple[str, str]], /, *,
                      reversible: bool = False)\
        -> _typing.Iterator[_util.FlashcardGroup]:
    for text, sem in map:
        yield _typing.cast(
            _util.FlashcardGroup,
            _util.TwoSidedFlashcard(
                text, sem,
                reversible=reversible,
            )
        )


def punctuation_hinter(hinted: _typing.Callable[[int], bool] = lambda _: True, *,
                       sanitizer: _typing.Callable[[str], str] = lambda str_: str_)\
        -> _typing.Callable[[int, str], tuple[str, str]]:
    def ret(index: int, str_: str) -> tuple[str, str]:
        if hinted(index):
            count: int = len(_misc.split_by_punctuations(sanitizer(str_)))
            return (f'→{count}', f'{count}←')
        return ('→', '←')
    return ret
