# -*- coding: UTF-8 -*-
import itertools as _itertools
import typing as _typing

from ..config import CONFIG
from ..util import (
    ClozeFlashcardGroup,
    FlashcardGroup,
    FlashcardStateGroup,
    LazyIterableSequence,
    StatefulFlashcardGroup,
    TwoSidedFlashcard,
    constant,
    identity,
    ignore_args,
)
from ._misc import split_by_punctuations


def attach_flashcard_states(
    flashcards: _typing.Iterable[FlashcardGroup],
    /,
    *,
    states: _typing.Iterable[FlashcardStateGroup],
) -> _typing.Iterator[StatefulFlashcardGroup]:
    for fc, st in zip(
        flashcards,
        _itertools.chain(states, _itertools.repeat(FlashcardStateGroup())),
    ):
        yield StatefulFlashcardGroup(flashcard=fc, state=st)


def listify_flashcards(
    flashcards: _typing.Iterable[StatefulFlashcardGroup],
) -> str:
    def ret_gen() -> _typing.Iterator[str]:
        newline: str = ""
        for index, flashcard in enumerate(flashcards):
            yield newline
            yield str(index + 1)
            yield ". "
            yield str(flashcard)
            newline = "\n"

    return "".join(ret_gen())


def memorize_two_sided0(
    strs: _typing.Iterable[str],
    /,
    *,
    offsets: _typing.Callable[[int], int | None] = constant(1),
    reversible: bool = True,
    hinter: _typing.Callable[[int, str], tuple[str, str]] = constant(("", "")),
) -> _typing.Iterator[FlashcardGroup]:
    @_typing.final
    class HintedStr(_typing.NamedTuple):
        str_: str
        left: str
        right: str

    strs_seq: _typing.Sequence[str] = LazyIterableSequence(strs)

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
        ret: TwoSidedFlashcard = TwoSidedFlashcard(
            left.str_ + right.left,
            left.right + right.str_,
            reversible=reversible,
        )
        assert isinstance(ret, FlashcardGroup)
        yield ret


def memorize_linked_seq0(
    strs: _typing.Iterable[str],
    /,
    hinter: _typing.Callable[[int, str], tuple[str, str]] = constant(("→", "←")),
    **kwargs: _typing.Any,
) -> _typing.Iterator[FlashcardGroup]:
    return memorize_two_sided0(
        strs,
        offsets=ignore_args(_itertools.chain((1,), _itertools.cycle((1, 0))).__next__),
        hinter=hinter,
        **kwargs,
    )


def memorize_indexed_seq0(
    strs: _typing.Iterable[str],
    /,
    *,
    indices: _typing.Callable[[int], int | None] = int(1).__add__,
    reversible: bool = True,
) -> _typing.Iterator[FlashcardGroup]:
    idx: int
    str_: str
    for idx, str_ in enumerate(strs):
        index: int | None = indices(idx)
        if index is None:
            continue
        ret: TwoSidedFlashcard = TwoSidedFlashcard(
            str(index),
            str_,
            reversible=reversible,
        )
        assert isinstance(ret, FlashcardGroup)
        yield ret


def semantics_seq_map0(
    map: _typing.Iterable[tuple[str, str]], /, *, reversible: bool = False
) -> _typing.Iterator[FlashcardGroup]:
    text: str
    sem: str
    for text, sem in map:
        ret: TwoSidedFlashcard = TwoSidedFlashcard(
            text,
            sem,
            reversible=reversible,
        )
        assert isinstance(ret, FlashcardGroup)
        yield ret


def punctuation_hinter(
    hinted: _typing.Callable[[int], bool] = constant(True),
    *,
    sanitizer: _typing.Callable[[str], str] = identity,
) -> _typing.Callable[[int, str], tuple[str, str]]:
    def ret(index: int, str_: str) -> tuple[str, str]:
        if hinted(index):
            count: int = sum(1 for _ in split_by_punctuations(sanitizer(str_)))
            return (f"→{count}", f"{count}←")
        return ("→", "←")

    return ret


def cloze_texts(
    texts: _typing.Iterable[str], /, *, token: tuple[str, str] = CONFIG.cloze_token
) -> _typing.Iterator[FlashcardGroup]:
    text: str
    for text in texts:
        ret: ClozeFlashcardGroup = ClozeFlashcardGroup(text, token=token)
        assert isinstance(ret, FlashcardGroup)
        yield ret
