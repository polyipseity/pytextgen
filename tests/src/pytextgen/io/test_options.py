"""Tests for `src/pytextgen/io/options.py` (GenOpts / ClearOpts)."""

from dataclasses import FrozenInstanceError

import pytest

from pytextgen.io.options import ClearOpts, ClearType, GenOpts

"""Public symbols exported by this module (none)."""
__all__ = ()


def test_clearopts_coercion():
    """ClearOpts coerces provided type values into a frozenset."""
    opts = ClearOpts(types={ClearType.CONTENT})
    assert isinstance(opts.types, frozenset)
    assert ClearType.CONTENT in opts.types


def test_cleartype_values_are_stable() -> None:
    """ClearType string values should remain stable for CLI compatibility."""
    assert ClearType.CONTENT.value == "content"
    assert ClearType.FLASHCARD_STATE.value == "fc_state"


def test_genopts_is_frozen_dataclass() -> None:
    """GenOpts should be immutable so options objects remain deterministic."""
    opts = GenOpts(timestamp=True, init_flashcards=False, compiler=compile)
    with pytest.raises(FrozenInstanceError):
        setattr(opts, "timestamp", False)
