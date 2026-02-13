"""Tests for `src/pytextgen/io/utils.py` (Result, FileSection helpers)."""

from pytextgen.io.utils import NULL_LOCATION, Result

__all__ = ()


def test_result_isinstance_guard():
    r = Result(location=NULL_LOCATION, text="hello")
    assert Result.isinstance(r)

    class Bad:
        pass

    assert not Result.isinstance(Bad())
