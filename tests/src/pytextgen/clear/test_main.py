"""Tests for `pytextgen.clear.main` parser and main behaviour."""

__all__ = ()


import argparse
from os import PathLike, fspath
from types import TracebackType
from typing import Any

import pytest
from anyio import Path

import pytextgen.clear.main as clear_main
from pytextgen.clear.main import Arguments, ExitCode
from pytextgen.io.options import ClearType


@pytest.mark.asyncio
async def test_clear_parser_parses_types_and_inputs(tmp_path: PathLike[str]):
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
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    seen = {}

    async def fake_main(args: Arguments):
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
    # prepare Arguments with one file
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    args = Arguments(inputs=(f,), types={ClearType.CONTENT})

    class BadCtx:
        async def __aenter__(self):
            raise RuntimeError("boom")

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
            return False

    class DummyWriter:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def write(self):
            return BadCtx()

    # monkeypatch ClearWriter used in clear.main
    monkeypatch.setattr(clear_main, "ClearWriter", DummyWriter)

    with pytest.raises(SystemExit) as excinfo:
        await clear_main.main(args)

    # SystemExit.code should equal the ExitCode.ERROR value
    assert isinstance(excinfo.value.code, clear_main.ExitCode)
    code = excinfo.value.code
    assert code & ExitCode.ERROR
