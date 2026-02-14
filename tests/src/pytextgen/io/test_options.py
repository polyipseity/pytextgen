"""Tests for `src/pytextgen/io/options.py` (GenOpts / ClearOpts)."""

from pytextgen.io.options import ClearOpts, ClearType

__all__ = ()


def test_clearopts_coercion():
    """ClearOpts coerces provided type values into a frozenset."""
    opts = ClearOpts(types={ClearType.CONTENT})
    assert isinstance(opts.types, frozenset)
    assert ClearType.CONTENT in opts.types
