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
from dataclasses import dataclass as _dc
from itertools import chain as _chain, cycle as _cycle, repeat as _repeat
from typing import (
    Any as _Any,
    Callable as _Call,
    Iterable as _Iter,
    Iterator as _Itor,
    final as _fin,
)


def attach_flashcard_states(flashcards: _Iter[_FcGrp], /, *, states: _Iter[_FcStGrp]):
    for fc, st in zip(flashcards, _chain(states, _repeat(_FcStGrp()))):
        yield _StFcGrp(flashcard=fc, state=st)


def listify_flashcards(
    flashcards: _Iter[_StFcGrp],
    /,
    *,
    ordered: bool = False,
):
    def ret_gen():
        newline = ""
        if ordered:
            for index, flashcard in enumerate(flashcards):
                yield newline
                yield str(index + 1)
                yield ". "
                yield str(flashcard)
                newline = "\n"
            return
        for flashcard in flashcards:
            yield newline
            yield "- "
            yield str(flashcard)
            newline = "\n"

    return "".join(ret_gen())


@_fin
@_dc(
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
    strs: _Iter[str],
    /,
    *,
    offsets: _Call[[int], int | None] = _const(1),
    reversible: bool = True,
    hinter: _Call[[int, str], tuple[str, str]] = _const(("", "")),
) -> _Itor[_FcGrp]:
    strs_seq = _IterSeq(iter(strs))  # Handles infinite sequences

    def offseted():
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

    iter_ = offseted()
    for left, right in zip(iter_, iter_):
        ret = _2SidedFc(
            left.str_ + right.left,
            left.right + right.str_,
            reversible=reversible,
        )
        assert isinstance(ret, _FcGrp)
        yield ret


def memorize_linked_seq0(
    strs: _Iter[str],
    /,
    hinter: _Call[[int, str], tuple[str, str]] = _const(("→", "←")),
    **kwargs: _Any,
):
    return memorize_two_sided0(
        strs,
        offsets=_ig_args(_chain((1,), _cycle((1, 0))).__next__),
        hinter=hinter,
        **kwargs,
    )


def memorize_indexed_seq0(
    strs: _Iter[str],
    /,
    *,
    indices: _Call[[int], int | None] = int(1).__add__,
    reversible: bool = True,
):
    for idx, str_ in enumerate(strs):
        index = indices(idx)
        if index is None:
            continue
        ret: _2SidedFc = _2SidedFc(str(index), str_, reversible=reversible)
        assert isinstance(ret, _FcGrp)
        yield ret


def semantics_seq_map0(map: _Iter[tuple[str, str]], /, *, reversible: bool = False):
    for text, sem in map:
        ret = _2SidedFc(text, sem, reversible=reversible)
        assert isinstance(ret, _FcGrp)
        yield ret


def punctuation_hinter(
    hinted: _Call[[int], bool] = _const(True), *, sanitizer: _Call[[str], str] = _id
):
    def ret(index: int, str: str):
        if hinted(index):
            count: int = sum(1 for _ in _spt_by_puncts(sanitizer(str)))
            return (f"→{count}", f"{count}←")
        return ("→", "←")

    return ret


def cloze_texts(texts: _Iter[str], /, *, token: tuple[str, str] = _CFG.cloze_token):
    for text in texts:
        ret: _CzFcGrp = _CzFcGrp(text, token=token)
        assert isinstance(ret, _FcGrp)
        yield ret
