# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import itertools as _itertools
import typing as _typing

from ..config import CONFIG as _CFG
from ..util import (
    ClozeFlashcardGroup as _CzFcGrp,
    FlashcardGroup as _FcGrp,
    FlashcardStateGroup as _FcStGrp,
    IteratorSequence as _IterSeq,
    StatefulFlashcardGroup as _StFcGrp,
    TwoSidedFlashcard as _2SidedFc,
    constant as _const,
    identity as _id,
    ignore_args as _ig_args,
    split_by_punctuations as _spt_by_puncts,
)


def attach_flashcard_states(
    flashcards: _typing.Iterable[_FcGrp],
    /,
    *,
    states: _typing.Iterable[_FcStGrp],
) -> _typing.Iterator[_StFcGrp]:
    for fc, st in zip(
        flashcards,
        _itertools.chain(states, _itertools.repeat(_FcStGrp())),
    ):
        yield _StFcGrp(flashcard=fc, state=st)


def listify_flashcards(
    flashcards: _typing.Iterable[_StFcGrp],
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


@_typing.final
@_dataclasses.dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=False,
    slots=True,
)
class _HintedStr:
    str_: str
    left: str
    right: str


def memorize_two_sided0(
    strs: _typing.Iterable[str],
    /,
    *,
    offsets: _typing.Callable[[int], int | None] = _const(1),
    reversible: bool = True,
    hinter: _typing.Callable[[int, str], tuple[str, str]] = _const(("", "")),
) -> _typing.Iterator[_FcGrp]:

    strs_seq: _typing.Sequence[str] = _IterSeq(iter(strs))  # Handles infinite sequences

    def offseted() -> _typing.Iterator[_HintedStr]:
        index = -1
        while True:
            offset = offsets(index)
            if offset is None:
                break
            index += offset
            try:
                str_ = strs_seq[index]
            except IndexError:
                break
            yield _HintedStr(str_, *hinter(index, str_))

    iter_: _typing.Iterator[_HintedStr] = offseted()
    for left, right in zip(iter_, iter_):
        ret: _2SidedFc = _2SidedFc(
            left.str_ + right.left,
            left.right + right.str_,
            reversible=reversible,
        )
        assert isinstance(ret, _FcGrp)
        yield ret


def memorize_linked_seq0(
    strs: _typing.Iterable[str],
    /,
    hinter: _typing.Callable[[int, str], tuple[str, str]] = _const(("→", "←")),
    **kwargs: _typing.Any,
) -> _typing.Iterator[_FcGrp]:
    return memorize_two_sided0(
        strs,
        offsets=_ig_args(_itertools.chain((1,), _itertools.cycle((1, 0))).__next__),
        hinter=hinter,
        **kwargs,
    )


def memorize_indexed_seq0(
    strs: _typing.Iterable[str],
    /,
    *,
    indices: _typing.Callable[[int], int | None] = int(1).__add__,
    reversible: bool = True,
) -> _typing.Iterator[_FcGrp]:
    idx: int
    str_: str
    for idx, str_ in enumerate(strs):
        index: int | None = indices(idx)
        if index is None:
            continue
        ret: _2SidedFc = _2SidedFc(
            str(index),
            str_,
            reversible=reversible,
        )
        assert isinstance(ret, _FcGrp)
        yield ret


def semantics_seq_map0(
    map: _typing.Iterable[tuple[str, str]], /, *, reversible: bool = False
) -> _typing.Iterator[_FcGrp]:
    text: str
    sem: str
    for text, sem in map:
        ret: _2SidedFc = _2SidedFc(
            text,
            sem,
            reversible=reversible,
        )
        assert isinstance(ret, _FcGrp)
        yield ret


def punctuation_hinter(
    hinted: _typing.Callable[[int], bool] = _const(True),
    *,
    sanitizer: _typing.Callable[[str], str] = _id,
) -> _typing.Callable[[int, str], tuple[str, str]]:
    def ret(index: int, str_: str) -> tuple[str, str]:
        if hinted(index):
            count: int = sum(1 for _ in _spt_by_puncts(sanitizer(str_)))
            return (f"→{count}", f"{count}←")
        return ("→", "←")

    return ret


def cloze_texts(
    texts: _typing.Iterable[str], /, *, token: tuple[str, str] = _CFG.cloze_token
) -> _typing.Iterator[_FcGrp]:
    text: str
    for text in texts:
        ret: _CzFcGrp = _CzFcGrp(text, token=token)
        assert isinstance(ret, _FcGrp)
        yield ret
