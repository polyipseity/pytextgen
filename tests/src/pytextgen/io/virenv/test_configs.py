"""Tests for `src/pytextgen/io/virenv/configs.py`."""

import pytest

from pytextgen.io.virenv.configs import CONFIG, FlashcardSeparatorType

"""Public symbols exported by this module (none)."""
__all__ = ()


def test_flashcard_separator_type_parse():
    """FlashcardSeparatorType.parse accepts short codes and returns flags."""
    t = FlashcardSeparatorType.parse("rm")
    assert t.reversible is True
    assert t.multiline is True

    t2 = FlashcardSeparatorType.parse("")
    assert t2.reversible is False
    assert t2.multiline is False


def test_flashcard_separator_type_parse_passthrough_instance() -> None:
    """Passing an instance should return that same instance unchanged."""
    expected = FlashcardSeparatorType(reversible=True, multiline=False)
    assert FlashcardSeparatorType.parse(expected) is expected


@pytest.mark.parametrize(
    ("options", "message"),
    (
        ("x", "Invalid option 'x'"),
        ("--", "Invalid options"),
        ("r-", "Incomplete options"),
    ),
)
def test_flashcard_separator_type_parse_rejects_invalid_options(
    options: str, message: str
) -> None:
    """Invalid compact option strings should raise ValueError with context."""
    with pytest.raises(ValueError, match=message):
        FlashcardSeparatorType.parse(options)


def test_config_has_expected_separators():
    """CONFIG exposes reasonable flashcard separator configurations."""
    keys = tuple(CONFIG.flashcard_separators.keys())
    assert any(k.reversible or k.multiline for k in keys)
    assert CONFIG.cloze_token[0].startswith("{")
