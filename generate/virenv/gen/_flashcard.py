import itertools as _itertools
import typing as _typing

from .. import util as _util
from . import *


def attach_flashcard_states(flashcards: _typing.Iterable[_util.FlashcardGroup], /, *,
                            states: _typing.Iterable[_util.FlashcardStateGroup]
                            ) -> _typing.Iterator[_util.StatefulFlashcardGroup]:
    for fc, st in zip(flashcards, _itertools.chain(states, _itertools.repeat(_util.FlashcardStateGroup()))):
        yield _util.StatefulFlashcardGroup(flashcard=fc, state=st)


def listify_flashcards(flashcards: _typing.Iterable[_util.StatefulFlashcardGroup]
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


def memorize_two_sided(strs: _typing.Iterable[str], /, *,
                       offsets: _typing.Callable[[int],
                                                 int | None] = _util.constant(1),
                       reversible: bool = True,
                       hinter: _typing.Callable[[
                           int, str], tuple[str, str]] = _util.constant(('→', '←')),
                       ) -> _typing.Iterator[_util.FlashcardGroup]:
    @_typing.final
    class HintedStr(_typing.NamedTuple):
        str_: str
        left: str
        right: str
    strs_seq: _typing.Sequence[str] = _util.LazyIterableSequence(strs)

    def offseted() -> _typing.Iterator[HintedStr]:
        index: int = -1
        while True:
            offset: int | None = offsets(index)
            if offset is None:
                break
            index += offset
            try:
                str_: str = strs_seq[index]
            except IndexError:
                break
            yield HintedStr(str_, *hinter(index, str_))
    iter: _typing.Iterator[HintedStr] = offseted()
    left: HintedStr
    right: HintedStr
    for left, right in zip(iter, iter):
        ret: _util.TwoSidedFlashcard = _util.TwoSidedFlashcard(
            left.str_ + right.left, left.right + right.str_,
            reversible=reversible,
        )
        assert isinstance(ret, _util.FlashcardGroup)
        yield ret


def memorize_linked_seq(strs: _typing.Iterable[str], /,
                        **kwargs: _typing.Any
                        ) -> _typing.Iterator[_util.FlashcardGroup]:
    return memorize_two_sided(strs,
                              offsets=_util.ignore_args(_itertools.chain(
                                  (1,), _itertools.cycle((1, 0,))).__next__),
                              **kwargs)


def memorize_indexed_seq(strs: _typing.Iterable[str], /, *,
                         indices: _typing.Callable[[
                             int], int | None] = int(1).__add__,
                         reversible: bool = True,
                         ) -> _typing.Iterator[_util.FlashcardGroup]:
    idx: int
    str_: str
    for idx, str_ in enumerate(strs):
        index: int | None = indices(idx)
        if index is None:
            continue
        ret: _util.TwoSidedFlashcard = _util.TwoSidedFlashcard(
            str(index), str_,
            reversible=reversible,
        )
        assert isinstance(ret, _util.FlashcardGroup)
        yield ret


def semantics_seq_map(map: _typing.Iterable[tuple[str, str]], /, *,
                      reversible: bool = False
                      ) -> _typing.Iterator[_util.FlashcardGroup]:
    text: str
    sem: str
    for text, sem in map:
        ret: _util.TwoSidedFlashcard = _util.TwoSidedFlashcard(
            text, sem,
            reversible=reversible,
        )
        assert isinstance(ret, _util.FlashcardGroup)
        yield ret


def punctuation_hinter(hinted: _typing.Callable[[int], bool] = _util.constant(True), *,
                       sanitizer: _typing.Callable[[str], str] = _util.identity
                       ) -> _typing.Callable[[int, str], tuple[str, str]]:
    def ret(index: int, str_: str) -> tuple[str, str]:
        if hinted(index):
            count: int = sum(
                1 for _ in split_by_punctuations(sanitizer(str_)))
            return (f'→{count}', f'{count}←')
        return ('→', '←')
    return ret


def cloze_texts(texts: _typing.Iterable[str], /, *,
                token: str = '==') -> _typing.Iterator[_util.FlashcardGroup]:
    text: str
    for text in texts:
        ret: _util.ClozeFlashcardGroup = _util.ClozeFlashcardGroup(
            text, token=token)
        assert isinstance(ret, _util.FlashcardGroup)
        yield ret
