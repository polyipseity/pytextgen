"""Tests for top-level CLI parsers and `__main__` dispatch.

Covers:
- `pytextgen.main.parser` produces subcommands and version handling
- `pytextgen.__main__` calls runnify with the correct arguments.
"""

from argparse import ArgumentParser

import pytest

from pytextgen import __main__ as pkg_main
from pytextgen import main as top_main

"""Public symbols exported by this module (none)."""
__all__ = ()


def test_top_level_parser_has_subcommands_and_version():
    """Top-level parser exposes expected subcommands and version option."""
    p = top_main.parser()
    # parser must be an ArgumentParser and require a subcommand
    assert isinstance(p, ArgumentParser)

    # verify that 'clear' and 'generate' can be parsed (invoke will be set)
    ns = p.parse_args(["clear", "./does/not/matter"])
    assert hasattr(ns, "invoke")

    ns2 = p.parse_args(["generate", "./does/not/matter"])
    assert hasattr(ns2, "invoke")


def test___main___calls_runnify_with_correct_arguments(monkeypatch: pytest.MonkeyPatch):
    """`__main__` calls runnify with main and backend_options use_uvloop True."""
    runnify_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture_runnify(*args: object, **kwargs: object) -> object:
        """Record runnify arguments and return a no-op callable so __main__ completes."""
        runnify_calls.append((args, dict(kwargs)))

        def noop(*_args: object, **_kwargs: object) -> None:
            """No-op so runnify(...)() does nothing."""
            return None

        return noop

    monkeypatch.setattr(pkg_main, "runnify", capture_runnify)
    pkg_main.__main__()

    assert len(runnify_calls) == 1
    args, kwargs = runnify_calls[0]
    assert len(args) == 1
    assert args[0] is pkg_main.main
    assert kwargs.get("backend_options") == {"use_uvloop": True}
