"""Tests for re-exports under :mod:`pytextgen.io.virenv.compat`."""

from pytextgen.io.virenv.compat import config as compat_config
from pytextgen.io.virenv.compat import gen as compat_gen
from pytextgen.io.virenv.compat import read as compat_read
from pytextgen.io.virenv.compat import util as compat_util
from pytextgen.io.virenv.configs import CONFIG, Configuration, FlashcardSeparatorType
from pytextgen.io.virenv.gen.users import memorize
from pytextgen.io.virenv.read import read_flashcard_states
from pytextgen.io.virenv.utils import export_seq

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_compat_config_reexports_identity() -> None:
    """compat.config should expose the same core configuration symbols."""
    assert compat_config.CONFIG is CONFIG
    assert compat_config.Configuration is Configuration
    assert compat_config.FlashcardSeparatorType is FlashcardSeparatorType
    assert set(compat_config.__all__) == {
        "FlashcardSeparatorType",
        "Configuration",
        "CONFIG",
    }


def test_compat_util_and_read_reexports_identity() -> None:
    """compat.util/read should re-export canonical helper callables."""
    assert compat_util.export_seq is export_seq
    assert compat_read.read_flashcard_states is read_flashcard_states


def test_compat_gen_reexports_selected_symbols() -> None:
    """compat.gen should expose known generator helpers from canonical modules."""
    assert "memorize" in compat_gen.__all__
    assert compat_gen.memorize is memorize
