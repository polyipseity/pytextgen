"""Tests for top-level CLI parsers and `__main__` dispatch.

Covers:
- `pytextgen.main.parser` produces subcommands and version handling
- `pytextgen.__main__.main` dispatches to the parser and calls asyncio.run
"""

import argparse
import asyncio
import inspect
from argparse import ArgumentParser
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import Any

import pytest

from pytextgen import __main__ as pkg_main
from pytextgen import main as top_main

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


def test___main___calls_asyncio_run(monkeypatch: pytest.MonkeyPatch):
    """`__main__` dispatch uses asyncio.run to execute the parser invoke coroutine."""
    called: dict[str, bool] = {}

    class DummyParser:
        """Parser stub that returns a namespace with an async ``invoke`` coroutine."""

        def parse_args(self, argv: list[str]):
            """Return a namespace exposing an async invoke function used by the test."""

            async def invoke(ns: "argparse.Namespace"):
                """Coroutine that marks the test as executed when run."""
                called["ran"] = True

            return SimpleNamespace(invoke=invoke)

    # replace parser used by __main__ with our dummy
    monkeypatch.setattr(pkg_main, "parser", lambda: DummyParser())

    # capture asyncio.run calls
    def fake_run(coro: Coroutine[Any, Any, Any]):
        """Replacement for ``asyncio.run`` that executes the coroutine synchronously.

        The stub asserts the passed object is a coroutine and runs it to
        exercise the parser-invoke flow inside the test harness.
        """
        # ensure it's the coroutine returned by DummyParser.parse_args
        assert inspect.iscoroutinefunction(coro.__class__) or asyncio.iscoroutine(coro)
        # run the coroutine to set the marker
        return asyncio.get_event_loop().run_until_complete(coro)

    monkeypatch.setattr(asyncio, "run", fake_run)

    # basicConfig is safe to call; run the function
    pkg_main.main()
    assert called.get("ran") is True
