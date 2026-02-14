"""Tests for `pytextgen.clear.main` parser and main behaviour."""

import argparse
from os import PathLike, fspath
from types import TracebackType
from typing import Any

import pytest
from anyio import Path

import pytextgen.clear.main as clear_main
from pytextgen.clear.main import Arguments, ExitCode
from pytextgen.io.options import ClearType

__all__ = ()


@pytest.mark.asyncio
async def test_clear_parser_parses_types_and_inputs(tmp_path: PathLike[str]):
    """Parser parses ClearType flags and input paths correctly."""
    # create a real file so Path.resolve(strict=True) in invoke works
    f = Path(tmp_path) / "in.md"
    await f.write_text("hello", encoding="utf-8")

    p = clear_main.parser()
    ns: argparse.Namespace = p.parse_args(["-t", "content", "--", fspath(f)])
    # argparse will convert the type strings into ClearType instances
    assert hasattr(ns, "types")
    assert isinstance(ns.types, (list, tuple, frozenset))


@pytest.mark.asyncio
async def test_clear_parser_invoke_calls_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: PathLike[str]
):
    """Parser's invoke resolves inputs and calls the clear `main` entry."""
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    seen = {}

    async def fake_main(args: Arguments):
        """Test helper that captures the invoked ``Arguments`` for assertion."""
        # ensure inputs have been resolved to Path and types preserved
        assert tuple(args.inputs)
        assert isinstance(args.types, frozenset)
        seen["args"] = args

    monkeypatch.setattr(clear_main, "main", fake_main)

    p = clear_main.parser()
    ns = p.parse_args([fspath(f)])
    # invoke is an async function; call and await it
    await ns.invoke(ns)
    assert "args" in seen


@pytest.mark.asyncio
async def test_clear_main_emits_exitcode_on_writer_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: PathLike[str]
):
    """`main` exits with an error `ExitCode` when writer fails on enter."""
    # prepare Arguments with one file
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    args = Arguments(inputs=(f,), types={ClearType.CONTENT})

    class BadCtx:
        """Context manager that raises on enter (used to simulate writer failure)."""

        async def __aenter__(self):
            """Simulate a failing __aenter__ by raising an exception."""
            raise RuntimeError("boom")

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
            """Exit handler used by the test; return False so the exception propagates."""
            return False

    class DummyWriter:
        """Minimal writer stub returning the failing context manager above."""

        def __init__(self, *a: Any, **k: Any) -> None:
            """Accept any args/kwargs; no real initialization required for test."""
            pass

        def write(self):
            """Return the ``BadCtx`` context manager used to emulate failure."""
            return BadCtx()

    # monkeypatch ClearWriter used in clear.main
    monkeypatch.setattr(clear_main, "ClearWriter", DummyWriter)

    with pytest.raises(SystemExit) as excinfo:
        await clear_main.main(args)

    # SystemExit.code should equal the ExitCode.ERROR value
    assert isinstance(excinfo.value.code, clear_main.ExitCode)
    code = excinfo.value.code
    assert code & ExitCode.ERROR
