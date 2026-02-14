"""Tests for `pytextgen.io.virenv.utils` helpers (merged).

This file consolidates flashcard-related unit tests previously split
across `test_utils_more.py` and `test_utils.py` in the same package.
"""

from datetime import date
from typing import cast

from pytextgen.io.virenv.utils import (
    ClozeFlashcardGroup,
    FlashcardGroup,
    FlashcardState,
    FlashcardStateGroup,
    StatefulFlashcardGroup,
    TwoSidedFlashcard,
    export_seq,
)

__all__ = ()


def test_flashcardstate_parse_and_str():
    """FlashcardState parses and formats as expected."""
    s = "!2023-01-02,10,250"
    st = FlashcardState.compile(s)
    assert st.date == date.fromisoformat("2023-01-02")
    assert st.interval == 10
    assert st.ease == 250
    assert str(st) == "!2023-01-02,10,250"


def test_flashcardstate_compile_many_empty():
    """compile_many yields empty iterator for input lacking states."""
    assert list(FlashcardState.compile_many("no states here")) == []


def test_TwoSidedFlashcard_str_len_and_indexing():
    """TwoSidedFlashcard string output, length and indexing behave."""
    f = TwoSidedFlashcard(left="L", right="R", reversible=True)
    s = str(f)
    assert "L" in s and "R" in s
    assert len(f) == 2
    assert f[0] == str(f)

    f2 = TwoSidedFlashcard(left="L", right="R", reversible=False)
    assert len(f2) == 1


def test_ClozeFlashcardGroup_extracts_tokens_and_len():
    """ClozeFlashcardGroup locates cloze tokens and reports their count."""
    txt = "This is a {{cloze}} example with {{two}} tokens"
    c = ClozeFlashcardGroup(context=txt, token=("{{", "}}"))
    assert len(c) == 2
    assert c[0] == "cloze"
    assert str(c) == txt


def test_FlashcardStateGroup_and_Stateful_str_and_compile():
    """FlashcardStateGroup serialises and parses; StatefulFlashcardGroup composes."""
    s1 = FlashcardState.compile("!2023-01-02,1,250")
    s2 = FlashcardState.compile("!2023-01-03,2,300")
    grp = FlashcardStateGroup((s1, s2))
    txt = str(grp)
    assert "SR:" in txt or txt.startswith("<!--SR:") or txt.endswith("-->")

    parsed = FlashcardStateGroup.compile(str(grp))
    assert len(parsed) == 2

    fc = TwoSidedFlashcard(left="a", right="b", reversible=True)
    stateful = StatefulFlashcardGroup(flashcard=cast(FlashcardGroup, fc), state=parsed)
    assert str(stateful).startswith(str(fc))


def test_export_seq_returns_name_map():
    """export_seq returns a mapping keyed by symbol name."""
    m = export_seq(TwoSidedFlashcard, ClozeFlashcardGroup)
    assert "TwoSidedFlashcard" in m and "ClozeFlashcardGroup" in m
