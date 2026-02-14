"""Tests for `pytextgen.generate.main` parser and main behaviour.

Covers parser flags, invoke wiring (CompileCache) and error-exit paths
(READ_ERROR, VALIDATE_ERROR, WRITE_ERROR) by monkeypatching Reader/Writer.
"""

from os import PathLike, fspath
from types import SimpleNamespace, TracebackType
from typing import Any, cast

import pytest
from anyio import Path

import pytextgen.generate.main as gen_main
from pytextgen.generate.main import Arguments, ExitCode
from pytextgen.io.options import GenOpts

__all__ = ()


def test_generate_parser_flags_defaults_and_overrides():
    """Parser default flags and explicit overrides behave as expected."""
    p = gen_main.parser()

    # default behaviour - timestamp True, init_flashcards False
    ns = p.parse_args(["./in.md"])  # default values
    assert ns.timestamp is True
    assert ns.init_flashcards is False
    assert ns.code_cache is not False

    # explicit no-timestamp and init-flashcards
    ns2 = p.parse_args(["-T", "--init-flashcards", "./in.md"])
    assert ns2.timestamp is False
    assert ns2.init_flashcards is True

    # explicit no-code-cache
    ns3 = p.parse_args(["--no-code-cache", "./in.md"])
    assert ns3.code_cache is None


@pytest.mark.asyncio
async def test_generate_parser_invoke_uses_CompileCache_and_calls_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: PathLike[str]
):
    """Parser's invoke uses `CompileCache` and delegates to `main`."""
    # create a real file so Path.resolve(strict=True) in invoke works
    f = Path(tmp_path) / "in.md"
    await f.write_text("hello", encoding="utf-8")

    seen = {}

    async def fake_main(args: Arguments):
        """Capture the Arguments passed to `main` when the parser's invoke is run."""
        assert isinstance(args.options, GenOpts)
        seen["args"] = args

    # monkeypatch the CompileCache used by the parser so we don't touch FS
    class DummyCache:
        """Substitute for :class:`CompileCache` used during parser-invoke tests."""

        def __init__(self, folder: Path):
            """Store the provided folder path (unused in the dummy)."""
            self.folder = folder

        async def __aenter__(self):
            """Enter and return a namespace exposing a ``compile`` callable."""
            return SimpleNamespace(compile=compile)

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
            """Exit the dummy context (no cleanup required)."""
            return False

    monkeypatch.setattr(gen_main, "CompileCache", DummyCache)
    monkeypatch.setattr(gen_main, "main", fake_main)

    p = gen_main.parser()
    ns = p.parse_args([fspath(f)])
    await ns.invoke(ns)
    assert "args" in seen


@pytest.mark.asyncio
async def test_generate_main_read_error_exits_with_read_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: PathLike[str]
):
    """`main` exits with READ_ERROR when reading fails."""
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    args = Arguments(
        inputs=(f,),
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    async def bad_cached(*, path: Path, options: GenOpts) -> None:
        """Simulate Reader.cached raising an error during read."""
        raise RuntimeError("read-fail")

    monkeypatch.setattr(gen_main, "Reader", SimpleNamespace(cached=bad_cached))

    with pytest.raises(SystemExit) as excinfo:
        await gen_main.main(args)

    assert isinstance(excinfo.value.code, gen_main.ExitCode)
    code = excinfo.value.code
    assert code & ExitCode.READ_ERROR


@pytest.mark.asyncio
async def test_generate_main_validate_and_write_errors(
    monkeypatch: "pytest.MonkeyPatch", tmp_path: PathLike[str]
):
    """Validation/write failures produce the appropriate ExitCode."""
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    class WriterGood:
        """Writer stub that successfully enters/exits its context."""

        def __init__(self, *a: Any, **k: Any) -> None:
            """No-op initializer for the test stub."""
            pass

        def write(self):
            """Return an async context manager used by this writer stub."""
            """Return an async context manager used by this writer stub."""

            class Ctx:
                """Async context manager used by the writer stub (enter/exit helpers)."""

                async def __aenter__(self) -> None:
                    """Succeed on enter (no validation error)."""
                    return None

                async def __aexit__(
                    self,
                    exc_type: type[BaseException] | None,
                    exc: BaseException | None,
                    tb: TracebackType | None,
                ) -> bool:
                    """Succeed on exit (do not suppress exceptions)."""
                    return False

            return Ctx()

    class WriterValidateBad:
        """Writer stub that raises an error during validation (enter)."""

        def __init__(self, *a: Any, **k: Any) -> None:
            """No-op initializer."""
            pass

        def write(self):
            """Return a context manager that raises on enter (validation error)."""

            class Ctx:
                """Context manager which raises on enter to simulate validation failure."""

                async def __aenter__(self) -> None:
                    """Simulate a validation error when the context is entered."""
                    raise RuntimeError("validate")

                async def __aexit__(
                    self,
                    exc_type: type[BaseException] | None,
                    exc: BaseException | None,
                    tb: TracebackType | None,
                ) -> bool:
                    """Exit handler that does not suppress the raised error."""
                    return False

            return Ctx()

    class WriterWriteBad:
        """Writer stub that raises an error during write (exit)."""

        def __init__(self, *a: Any, **k: Any) -> None:
            """No-op initializer for the test stub."""
            pass

        def write(self):
            """Return a context manager that raises on exit to simulate write failure."""

            class Ctx:
                """Context manager which raises during __aexit__ to emulate write error."""

                async def __aenter__(self) -> None:
                    """Succeed on enter so error appears during exit."""
                    return None

                async def __aexit__(
                    self,
                    exc_type: type[BaseException] | None,
                    exc: BaseException | None,
                    tb: TracebackType | None,
                ) -> bool:
                    """Raise a write-time error to simulate write failure."""
                    raise RuntimeError("write")

            return Ctx()

    # Reader.cached should return an object whose pipe() yields writers
    class ReaderObj:
        """Small reader-like object whose ``pipe`` yields different writers.

        The behaviour depends on ``which`` so tests can exercise different
        error paths (validate/write/good).
        """

        def __init__(self, which: str):
            """Store which behaviour this reader object should expose."""
            self.which = which

        def pipe(self):
            """Return a sequence of writer instances according to the ``which`` value."""
            if self.which == "good":
                return [WriterGood()]
            if self.which == "validate":
                return [WriterValidateBad()]
            return [WriterWriteBad()]

    async def reader_cached(*, path: Path, options: GenOpts):
        """Return a test ``Reader``-like object selected by filename suffix.

        This helper is installed as ``Reader.cached`` during the test so the
        main flow exercises different writer outcomes based on the file name.
        """
        # return different reader instances depending on filename
        name = fspath(path)
        if name.endswith("validate.md"):
            return ReaderObj("validate")
        if name.endswith("write.md"):
            return ReaderObj("write")
        return ReaderObj("good")

    monkeypatch.setattr(gen_main, "Reader", SimpleNamespace(cached=reader_cached))

    # 1) validation error
    f_validate = Path(tmp_path) / "validate.md"
    await f_validate.write_text("x", encoding="utf-8")
    args_validate = Arguments(
        inputs=(f_validate,),
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    with pytest.raises(SystemExit) as excinfo1:
        await gen_main.main(args_validate)
    code1 = cast(gen_main.ExitCode, excinfo1.value.code)
    assert code1 & ExitCode.VALIDATE_ERROR

    # 2) write error
    f_write = Path(tmp_path) / "write.md"
    await f_write.write_text("x", encoding="utf-8")
    args_write = Arguments(
        inputs=(f_write,),
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    with pytest.raises(SystemExit) as excinfo2:
        await gen_main.main(args_write)
    code2 = cast(gen_main.ExitCode, excinfo2.value.code)
    assert code2 & ExitCode.WRITE_ERROR
