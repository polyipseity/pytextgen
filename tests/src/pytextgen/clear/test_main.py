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

"""Public symbols exported by this module (none)."""
__all__ = ()


@pytest.mark.anyio
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


@pytest.mark.anyio
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


@pytest.mark.anyio
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


@pytest.mark.anyio
async def test_clear_main_success_exits_with_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: PathLike[str],
) -> None:
    """Successful writes should exit with zero-valued ``ExitCode``."""
    f = Path(tmp_path) / "ok.md"
    await f.write_text("x", encoding="utf-8")

    args = Arguments(inputs=(f,), types={ClearType.CONTENT})

    class OkCtx:
        """Context manager stub that succeeds on enter/exit."""

        async def __aenter__(self) -> None:
            """Succeed immediately."""
            return None

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
            """Do not suppress exceptions."""
            return False

    class OkWriter:
        """Writer stub returning a successful async context manager."""

        def __init__(self, *a: Any, **k: Any) -> None:
            """Accept any constructor inputs from production call sites."""
            pass

        def write(self):
            """Return successful context manager."""
            return OkCtx()

    monkeypatch.setattr(clear_main, "ClearWriter", OkWriter)

    with pytest.raises(SystemExit) as excinfo:
        await clear_main.main(args)

    assert isinstance(excinfo.value.code, clear_main.ExitCode)
    assert clear_main.ExitCode(excinfo.value.code) == ExitCode(0)


@pytest.mark.anyio
async def test_clear_main_multiple_failures_still_emit_error_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: PathLike[str],
) -> None:
    """Multiple failing inputs should still produce the aggregated error flag."""
    f1 = Path(tmp_path) / "a.md"
    f2 = Path(tmp_path) / "b.md"
    await f1.write_text("x", encoding="utf-8")
    await f2.write_text("x", encoding="utf-8")

    args = Arguments(inputs=(f1, f2), types={ClearType.CONTENT})

    class BadCtx:
        """Context manager stub that fails on enter."""

        async def __aenter__(self) -> None:
            """Raise a write failure during enter."""
            raise RuntimeError("boom")

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
            """Do not suppress exceptions."""
            return False

    class BadWriter:
        """Writer stub returning the failing context manager."""

        def __init__(self, *a: Any, **k: Any) -> None:
            """Accept any constructor inputs from production call sites."""
            pass

        def write(self):
            """Return failing context manager."""
            return BadCtx()

    monkeypatch.setattr(clear_main, "ClearWriter", BadWriter)

    with pytest.raises(SystemExit) as excinfo:
        await clear_main.main(args)

    code = clear_main.ExitCode(excinfo.value.code)
    assert code & ExitCode.ERROR
