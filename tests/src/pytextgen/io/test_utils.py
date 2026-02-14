"""Tests for `src/pytextgen/io/utils.py` (Result, FileSection helpers)."""

from pytextgen.io.utils import NULL_LOCATION, Result

__all__ = ()


def test_result_isinstance_guard():
    """Result.isinstance returns True for matching shape and False otherwise."""
    r = Result(location=NULL_LOCATION, text="hello")
    assert Result.isinstance(r)

    class Bad:
        """Type intentionally not matching ``Result`` shape for negative test."""

        pass

    assert not Result.isinstance(Bad())
