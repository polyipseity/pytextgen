"""Tests for `src/pytextgen/io/virenv/configs.py`."""

from pytextgen.io.virenv.configs import CONFIG, FlashcardSeparatorType

__all__ = ()


def test_flashcard_separator_type_parse():
    t = FlashcardSeparatorType.parse("rm")
    assert t.reversible is True
    assert t.multiline is True

    t2 = FlashcardSeparatorType.parse("")
    assert t2.reversible is False
    assert t2.multiline is False


def test_config_has_expected_separators():
    keys = tuple(CONFIG.flashcard_separators.keys())
    assert any(k.reversible or k.multiline for k in keys)
    assert CONFIG.cloze_token[0].startswith("{")
