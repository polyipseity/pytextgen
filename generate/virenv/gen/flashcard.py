import itertools as _itertools
import typing as _typing

from .... import util as _util
from .. import util as _util1
from . import misc as _misc


def attach_flashcard_states(flashcards: _typing.Iterable[_util1.FlashcardGroup], /, *,
                            states: _typing.Iterable[_util1.FlashcardStateGroup]
                            ) -> _typing.Iterator[_util1.StatefulFlashcardGroup]:
    for fc, st in zip(flashcards, _itertools.chain(states, _itertools.repeat(_util1.FlashcardStateGroup()))):
        yield _util1.StatefulFlashcardGroup(flashcard=fc, state=st)


def listify_flashcards(flashcards: _typing.Iterable[_util1.StatefulFlashcardGroup]
                       ) -> str:
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
                        hinter: _typing.Callable[[
                            int, str], tuple[str, str]] = _util.constant(('→', '←')),
                        ) -> _typing.Iterator[_util1.FlashcardGroup]:
    class HintedStr(_typing.NamedTuple):
        str_: str
        left: str
        right: str
    iter: enumerate[str] = enumerate(strs)
    index: int
    str_: str
    try:
        index, str_ = next(iter)
    except StopIteration:
        return
    prev: HintedStr = HintedStr(str_, *hinter(index, str_))
    for index, str_ in iter:
        cur: HintedStr = HintedStr(str_, *hinter(index, str_))
        ret: _util1.TwoSidedFlashcard = _util1.TwoSidedFlashcard(
            prev.str_ + cur.left, prev.right + cur.str_,
            reversible=reversible,
        )
        assert isinstance(ret, _util1.FlashcardGroup)
        yield ret
        prev = cur


def memorize_indexed_seq(strs: _typing.Iterable[str], /, *,
                         indices: _typing.Callable[[
                             int], int | None] = int(1).__add__,
                         reversible: bool = True,
                         ) -> _typing.Iterator[_util1.FlashcardGroup]:
    idx: int
    str_: str
    for idx, str_ in enumerate(strs):
        index: int | None = indices(idx)
        if index is None:
            continue
        ret: _util1.TwoSidedFlashcard = _util1.TwoSidedFlashcard(
            str(index), str_,
            reversible=reversible,
        )
        assert isinstance(ret, _util1.FlashcardGroup)
        yield ret


def semantics_seq_map(map: _typing.Iterable[tuple[str, str]], /, *,
                      reversible: bool = False
                      ) -> _typing.Iterator[_util1.FlashcardGroup]:
    text: str
    sem: str
    for text, sem in map:
        ret: _util1.TwoSidedFlashcard = _util1.TwoSidedFlashcard(
            text, sem,
            reversible=reversible,
        )
        assert isinstance(ret, _util1.FlashcardGroup)
        yield ret


def punctuation_hinter(hinted: _typing.Callable[[int], bool] = _util.constant(True), *,
                       sanitizer: _typing.Callable[[str], str] = _util.identity
                       ) -> _typing.Callable[[int, str], tuple[str, str]]:
    def ret(index: int, str_: str) -> tuple[str, str]:
        if hinted(index):
            count: int = sum(
                1 for _ in _misc.split_by_punctuations(sanitizer(str_)))
            return (f'→{count}', f'{count}←')
        return ('→', '←')
    return ret
