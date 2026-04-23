"""Tests for :mod:`pytextgen.io.virenv.meta`."""

from pytextgen.io.virenv.configs import CONFIG
from pytextgen.io.virenv.meta import dirty

"""Public symbols exported by this test module (none)."""
__all__ = ()


def test_dirty_is_false_for_default_configuration() -> None:
    """`dirty()` should be false when runtime config matches defaults."""
    assert dirty() is False


def test_dirty_is_true_after_configuration_mutation() -> None:
    """`dirty()` should detect modified runtime configuration and then reset."""
    old = CONFIG.cloze_token
    try:
        CONFIG.cloze_token = ("{{", "}}")
        assert dirty() is True
    finally:
        CONFIG.cloze_token = old

    assert dirty() is False
