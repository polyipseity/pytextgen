"""Tests for :mod:`pytextgen.generate.__main__` entry-point behavior."""

import pytest

from pytextgen.generate import __main__ as generate_main
from tests.utils import RunModuleHelper

"""Public symbols exported by this test module (none)."""
__all__ = ()


class _Entry:
    """Small awaitable-invoke namespace used by CLI dispatch tests."""

    def __init__(self) -> None:
        """Initialise call-tracking state."""
        self.called = False
        self.arg: object | None = None

    async def invoke(self, arg: object) -> None:
        """Record invocation arguments for assertions."""
        self.called = True
        self.arg = arg


class _Parser:
    """Parser stub returning a preconfigured entry object."""

    def __init__(self, entry: _Entry) -> None:
        """Store the entry instance returned by ``parse_args``."""
        self.entry = entry
        self.args: list[str] | None = None

    def parse_args(self, args: list[str]) -> _Entry:
        """Capture argument list and return the configured entry."""
        self.args = list(args)
        return self.entry


@pytest.mark.anyio
async def test_main_parses_argv_and_invokes_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`main` should parse argv (excluding program) and invoke parsed entry."""
    entry = _Entry()
    parser = _Parser(entry)

    monkeypatch.setattr(generate_main, "parser", lambda: parser)
    monkeypatch.setattr(
        generate_main,
        "argv",
        ["pytextgen_generate", "--no-code-cache", "in.md"],
    )

    await generate_main.main()

    assert parser.args == ["--no-code-cache", "in.md"]
    assert entry.called is True
    assert entry.arg is entry


def test___main___script_guard_uses_runnify(run_module_helper: RunModuleHelper) -> None:
    """Running module as script should execute the ``runnify`` wrapper path."""
    called = run_module_helper("pytextgen.generate.__main__", ["pytextgen_generate"])
    assert called["ran"] is True
