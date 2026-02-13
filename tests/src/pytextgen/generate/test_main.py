"""Tests for `pytextgen.generate.main` parser and main behaviour.

Covers parser flags, invoke wiring (CompileCache) and error-exit paths
(READ_ERROR, VALIDATE_ERROR, WRITE_ERROR) by monkeypatching Reader/Writer.
"""

__all__ = ()

from os import PathLike, fspath
from types import SimpleNamespace, TracebackType
from typing import Any, cast

import pytest
from anyio import Path

import pytextgen.generate.main as gen_main
from pytextgen.generate.main import Arguments, ExitCode
from pytextgen.io.options import GenOpts


def test_generate_parser_flags_defaults_and_overrides():
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
    # create a real file so Path.resolve(strict=True) in invoke works
    f = Path(tmp_path) / "in.md"
    await f.write_text("hello", encoding="utf-8")

    seen = {}

    async def fake_main(args: Arguments):
        assert isinstance(args.options, GenOpts)
        seen["args"] = args

    # monkeypatch the CompileCache used by the parser so we don't touch FS
    class DummyCache:
        def __init__(self, folder: Path):
            self.folder = folder

        async def __aenter__(self):
            return SimpleNamespace(compile=compile)

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> bool:
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
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    args = Arguments(
        inputs=(f,),
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    async def bad_cached(*, path: Path, options: GenOpts) -> None:
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
    f = Path(tmp_path) / "in.md"
    await f.write_text("x", encoding="utf-8")

    class WriterGood:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def write(self):
            class Ctx:
                async def __aenter__(self) -> None:
                    return None

                async def __aexit__(
                    self,
                    exc_type: type[BaseException] | None,
                    exc: BaseException | None,
                    tb: TracebackType | None,
                ) -> bool:
                    return False

            return Ctx()

    class WriterValidateBad:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def write(self):
            class Ctx:
                async def __aenter__(self) -> None:
                    raise RuntimeError("validate")

                async def __aexit__(
                    self,
                    exc_type: type[BaseException] | None,
                    exc: BaseException | None,
                    tb: TracebackType | None,
                ) -> bool:
                    return False

            return Ctx()

    class WriterWriteBad:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def write(self):
            class Ctx:
                async def __aenter__(self) -> None:
                    return None

                async def __aexit__(
                    self,
                    exc_type: type[BaseException] | None,
                    exc: BaseException | None,
                    tb: TracebackType | None,
                ) -> bool:
                    raise RuntimeError("write")

            return Ctx()

    # Reader.cached should return an object whose pipe() yields writers
    class ReaderObj:
        def __init__(self, which: str):
            self.which = which

        def pipe(self):
            if self.which == "good":
                return [WriterGood()]
            if self.which == "validate":
                return [WriterValidateBad()]
            return [WriterWriteBad()]

    async def reader_cached(*, path: Path, options: GenOpts):
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
