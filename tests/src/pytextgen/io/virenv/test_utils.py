"""Tests for `src/pytextgen/io/virenv/utils.py` (FlashcardState).

Mirrors the source layout: `src/pytextgen/io/virenv/utils.py` →
`tests/src/pytextgen/io/virenv/test_utils.py`.
"""

from datetime import date

from pytextgen.io.virenv.utils import FlashcardState

__all__ = ()


def test_flashcardstate_parse_and_str():
    s = "!2023-01-02,10,250"
    st = FlashcardState.compile(s)
    assert st.date == date.fromisoformat("2023-01-02")
    assert st.interval == 10
    assert st.ease == 250
    assert str(st) == "!2023-01-02,10,250"


def test_flashcardstate_compile_many_empty():
    assert list(FlashcardState.compile_many("no states here")) == []
