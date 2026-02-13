"""Tests for `pytextgen.io.write.PythonWriter` behavior.

Verifies that executed code producing `Result` objects writes to the target
`PathLocation` and respects the `timestamp` option.
"""

__all__ = ()

from ast import parse
from datetime import datetime
from os import PathLike, fspath
from types import CodeType
from typing import cast

import pytest
from anyio import Path

from pytextgen.io.env import Environment
from pytextgen.io.options import GenOpts
from pytextgen.io.utils import Location, PathLocation, Result
from pytextgen.io.write import PythonWriter
from pytextgen.meta import GENERATE_COMMENT_FORMAT, GENERATE_COMMENT_REGEX


def _compile_returning_result(source: str, filename: str) -> CodeType:
    """Helper: compile a small snippet that returns a Result via make_result."""
    module_ast = parse(source, filename=filename, mode="exec", type_comments=True)

    ast0 = Environment.transform_code(module_ast)
    return compile(ast0, filename, "exec")


@pytest.mark.asyncio
async def test_PythonWriter_writes_result_to_path(tmp_path: PathLike[str]):
    out = Path(tmp_path) / "out.txt"

    # factory available in environment will create Result objects pointing to PathLocation
    def make_result(text: str):
        return Result(location=cast(Location, PathLocation(path=out)), text=text)

    env = Environment(globals={"make_result": make_result})

    code = _compile_returning_result("return make_result('hello')", fspath(out))
    writer = PythonWriter(
        code,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=False, init_flashcards=False, compiler=compile),
    )

    # create the target file so lock_file.resolve(strict=True) succeeds
    await out.write_text("", encoding="utf-8")

    async with writer.write():
        pass

    # file should contain the raw text (no timestamp header)
    assert await out.read_text(encoding="utf-8") == "hello"


@pytest.mark.asyncio
async def test_PythonWriter_respects_timestamp_option(tmp_path: PathLike[str]):
    out = Path(tmp_path) / "out2.txt"

    def make_result(text: str):
        return Result(location=cast(Location, PathLocation(path=out)), text=text)

    env = Environment(globals={"make_result": make_result})

    code = _compile_returning_result("return make_result('world')", fspath(out))
    writer = PythonWriter(
        code,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    # ensure file exists so lock_file.resolve(strict=True) succeeds
    await out.write_text("", encoding="utf-8")

    async with writer.write():
        pass

    txt = await out.read_text(encoding="utf-8")
    # should end with the returned text and include the generated comment
    assert txt.endswith("world")
    assert "generated at" in txt or txt.startswith(
        "<!-- The following content is generated"
    )


@pytest.mark.asyncio
async def test_PythonWriter_generates_valid_timestamp_format(tmp_path: PathLike[str]):
    out = Path(tmp_path) / "ts_format.txt"

    def make_result(text: str):
        return Result(location=cast(Location, PathLocation(path=out)), text=text)

    env = Environment(globals={"make_result": make_result})

    code = _compile_returning_result("return make_result('payload')", fspath(out))
    writer = PythonWriter(
        code,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    await out.write_text("", encoding="utf-8")

    async with writer.write():
        pass

    txt = await out.read_text(encoding="utf-8")
    m = GENERATE_COMMENT_REGEX.match(txt)
    assert m is not None, "generated comment did not match expected regex"

    ts = m.group(1)
    # ensure timestamp is parseable ISO format with tzinfo and microseconds
    parsed = datetime.fromisoformat(ts)
    assert parsed.tzinfo is not None
    assert parsed.microsecond >= 0

    # the header in the file should equal the formatted comment using the captured ts
    assert txt.startswith(GENERATE_COMMENT_FORMAT.format(now=ts))


@pytest.mark.asyncio
async def test_PythonWriter_concatenates_multiple_results(tmp_path: PathLike[str]):
    out = Path(tmp_path) / "multi.txt"

    def make_result(text: str):
        return Result(location=cast(Location, PathLocation(path=out)), text=text)

    env = Environment(globals={"make_result": make_result})

    code = _compile_returning_result(
        "return [make_result('first'), make_result('second')]", fspath(out)
    )
    writer = PythonWriter(
        code,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=False, init_flashcards=False, compiler=compile),
    )

    await out.write_text("", encoding="utf-8")

    async with writer.write():
        pass

    assert await out.read_text(encoding="utf-8") == "firstsecond"


@pytest.mark.asyncio
async def test_PythonWriter_ignores_empty_result_and_does_not_truncate(
    tmp_path: PathLike[str],
):
    out = Path(tmp_path) / "ignore_empty.txt"

    def make_result(text: str):
        return Result(location=cast(Location, PathLocation(path=out)), text=text)

    env = Environment(globals={"make_result": make_result})

    # pre-populate file so an empty-result must NOT erase it
    await out.write_text("preserve-me", encoding="utf-8")

    code = _compile_returning_result("return make_result('')", fspath(out))
    writer = PythonWriter(
        code,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )

    async with writer.write():
        pass

    # file must be unchanged (no timestamp inserted either)
    assert await out.read_text(encoding="utf-8") == "preserve-me"


@pytest.mark.asyncio
async def test_PythonWriter_timestamp_only_when_nonempty_write(tmp_path: PathLike[str]):
    out = Path(tmp_path) / "ts.txt"

    def make_result(text: str):
        return Result(location=cast(Location, PathLocation(path=out)), text=text)

    env = Environment(globals={"make_result": make_result})

    # ensure file exists
    await out.write_text("", encoding="utf-8")

    # empty-result with timestamp=True should NOT add a header
    code_empty = _compile_returning_result("return make_result('')", fspath(out))
    writer_empty = PythonWriter(
        code_empty,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )
    async with writer_empty.write():
        pass
    assert await out.read_text(encoding="utf-8") == ""

    # non-empty should add the generated comment when timestamp=True
    code_nonempty = _compile_returning_result(
        "return make_result('payload')", fspath(out)
    )
    writer_nonempty = PythonWriter(
        code_nonempty,
        init_codes=(),
        env=env,
        options=GenOpts(timestamp=True, init_flashcards=False, compiler=compile),
    )
    async with writer_nonempty.write():
        pass
    txt = await out.read_text(encoding="utf-8")
    assert txt.endswith("payload")
    assert "generated at" in txt or txt.startswith(
        "<!-- The following content is generated"
    )
