"""Helpers for constructing and formatting flashcards used by generators."""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import chain, cycle, repeat
from typing import (
    Any,
    Callable,
    final,
)

from ..configs import CONFIG
from ..utils import (
    ClozeFlashcardGroup,
    FlashcardGroup,
    FlashcardStateGroup,
    IteratorSequence,
    StatefulFlashcardGroup,
    TwoSidedFlashcard,
    constant,
    identity,
    ignore_args,
    split_by_punctuations,
)

__all__ = (
    "attach_flashcard_states",
    "listify_flashcards",
    "memorize_two_sided0",
    "memorize_linked_seq0",
    "memorize_indexed_seq0",
    "semantics_seq_map0",
    "punctuation_hinter",
    "cloze_texts",
)


def attach_flashcard_states(
    flashcards: Iterable[FlashcardGroup], /, *, states: Iterable[FlashcardStateGroup]
):
    """Pair flashcards with provided state entries.

    Yields `StatefulFlashcardGroup` instances by zipping flashcards with
    the provided `states` sequence, filling missing states with empty groups.
    """
    for fc, st in zip(flashcards, chain(states, repeat(FlashcardStateGroup()))):
        yield StatefulFlashcardGroup(flashcard=fc, state=st)


def listify_flashcards(
    flashcards: Iterable[StatefulFlashcardGroup],
    /,
    *,
    ordered: bool = False,
):
    """Return a Markdown list rendering of the flashcards.

    When `ordered=True` renders an ordered list, otherwise a bullet list.
    """

    def ret_gen():
        """Generator which emits the textual pieces used to build the Markdown list.

        Yields fragments that are later joined to produce either an ordered or
        unordered Markdown list depending on the ``ordered`` flag.
        """
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


@final
@dataclass(
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
    """Small container holding a hint-annotated string and its left/right hints."""

    str_: str
    left: str
    right: str


def memorize_two_sided0(
    strs: Iterable[str],
    /,
    *,
    offsets: Callable[[int], int | None] = constant(1),
    reversible: bool = True,
    hinter: Callable[[int, str], tuple[str, str]] = constant(("", "")),
) -> Iterator[FlashcardGroup]:
    """Turn a sequence of strings into paired two-sided flashcards.

    `offsets` controls how input indices are grouped, and `hinter` may add
    per-item annotations to the left/right parts.
    """
    strs_seq = IteratorSequence(iter(strs))  # Handles infinite sequences

    def offseted():
        """Yield _HintedStr items by advancing through ``strs_seq`` using ``offsets``.

        Advances the sequence by calling ``offsets(index)`` and stops when the
        callable returns ``None`` or the underlying sequence is exhausted.
        """
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
        ret = TwoSidedFlashcard(
            left.str_ + right.left,
            left.right + right.str_,
            reversible=reversible,
        )
        assert isinstance(ret, FlashcardGroup)
        yield ret


def memorize_linked_seq0(
    strs: Iterable[str],
    /,
    hinter: Callable[[int, str], tuple[str, str]] = constant(("→", "←")),
    **kwargs: Any,
):
    """Create linked-sequence two-sided flashcards from `strs`.

    Uses an alternating offsets pattern to link adjacent items into pairs.
    """
    return memorize_two_sided0(
        strs,
        offsets=ignore_args(chain((1,), cycle((1, 0))).__next__),
        hinter=hinter,
        **kwargs,
    )


def memorize_indexed_seq0(
    strs: Iterable[str],
    /,
    *,
    indices: Callable[[int], int | None] = int(1).__add__,
    reversible: bool = True,
):
    """Create indexed two-sided flashcards from `strs` using `indices`.

    For each item, `indices(idx)` determines the left-side index or
    skips the item if it returns ``None``.
    """
    for idx, str_ in enumerate(strs):
        index = indices(idx)
        if index is None:
            continue
        ret: TwoSidedFlashcard = TwoSidedFlashcard(
            str(index), str_, reversible=reversible
        )
        assert isinstance(ret, FlashcardGroup)
        yield ret


def semantics_seq_map0(map: Iterable[tuple[str, str]], /, *, reversible: bool = False):
    """Turn an iterator of ``(text, sem)`` pairs into flashcard groups.

    Each pair becomes a two-sided flashcard with `text` as the prompt and
    `sem` as the semantic value.
    """
    for text, sem in map:
        ret = TwoSidedFlashcard(text, sem, reversible=reversible)
        assert isinstance(ret, FlashcardGroup)
        yield ret


def punctuation_hinter(
    hinted: Callable[[int], bool] = constant(True),
    *,
    sanitizer: Callable[[str], str] = identity,
):
    """Return a hinter function that annotates hints using punctuation counts.

    The returned function yields left/right hint annotations based on the
    number of punctuation-boundary splits in the sanitized text.
    """

    def ret(index: int, str: str):
        """Return left/right hint tokens for ``str`` based on punctuation count.

        Uses ``sanitizer`` and ``split_by_punctuations`` to derive an integer
        hint which is embedded into the left/right tokens. When the item is
        not hinted the default arrows are returned.
        """
        if hinted(index):
            count: int = sum(1 for _ in split_by_punctuations(sanitizer(str)))
            return (f"→{count}", f"{count}←")
        return ("→", "←")

    return ret


def cloze_texts(
    texts: Iterable[str], /, *, token: tuple[str, str] = CONFIG.cloze_token
):
    """Yield cloze-style flashcard groups for each input text using `token`."""
    for text in texts:
        ret: ClozeFlashcardGroup = ClozeFlashcardGroup(text, token=token)
        assert isinstance(ret, FlashcardGroup)
        yield ret
