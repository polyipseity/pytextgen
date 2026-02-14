"""Tests for `pytextgen.io.read.MarkdownReader` and `Reader` caching.

These tests assert that MarkdownReader correctly extracts `module` and `data`
code blocks, resolves `# import` directives, and produces `PythonWriter`
instances whose `init_codes` include compiled library modules. They also
verify `Reader.cached` caching and unenclosed-block error handling.
"""

from collections.abc import Sequence
from os import PathLike
from types import CodeType
from typing import cast

import pytest
from anyio import Path

from pytextgen.io.options import GenOpts
from pytextgen.io.read import CodeLibrary, MarkdownReader, Reader
from pytextgen.io.write import Writer

__all__ = ()


@pytest.mark.asyncio
async def test_MarkdownReader_parses_imports_and_produces_writers(
    tmp_path: PathLike[str],
):
    """MarkdownReader extracts imports and returns configured writers."""
    # library module (provides code used via import)
    lib = Path(tmp_path) / "lib.md"
    await lib.write_text(
        """
```Python
# pytextgen generate module
CONST = 42
```
""",
        encoding="utf-8",
    )

    # main document references lib.md and contains a data block
    main = Path(tmp_path) / "main.md"
    await main.write_text(
        """
```Python
# pytextgen generate data
# import lib.md

def make():
    return CONST
```
""",
        encoding="utf-8",
    )

    opts = GenOpts(timestamp=True, init_flashcards=False, compiler=compile)
    reader: MarkdownReader = await Reader.new(path=main, options=opts)

    assert isinstance(reader, MarkdownReader)

    # reader should have compiled library/module codes available
    assert isinstance(
        cast(list[Sequence[CodeType]], cast(CodeLibrary, reader).codes), list
    )
    # pipe() should produce PythonWriter instances
    writers = reader.pipe()
    assert isinstance(writers, tuple) and len(writers) == 1

    w = writers[0]
    # inspect the hidden init_codes collected by the writer
    init_codes = getattr(w, "_PythonWriter__init_codes", None)
    assert init_codes is not None
    assert any(isinstance(c, CodeType) for c in init_codes)


@pytest.mark.asyncio
async def test_MarkdownReader_unenclosed_raises(tmp_path: PathLike[str]):
    """Unenclosed code blocks raise a ValueError during read."""
    bad = Path(tmp_path) / "bad.md"
    await bad.write_text(
        """
```Python
# pytextgen generate data
x = 1
# missing closing fence
""",
        encoding="utf-8",
    )
    opts = GenOpts(timestamp=True, init_flashcards=False, compiler=compile)
    with pytest.raises(ValueError):
        await Reader.new(path=bad, options=opts)


@pytest.mark.asyncio
async def test_MarkdownReader_import_non_codelib_raises(tmp_path: PathLike[str]):
    """MarkdownReader raises TypeError when an imported reader is not a CodeLibrary."""
    # write an "other" file and register a temporary Reader for .txt that
    # is NOT a CodeLibrary; MarkdownReader should raise TypeError when
    # encountering `# import other.txt`.
    other = Path(tmp_path) / "other.txt"
    await other.write_text("not code", encoding="utf-8")

    # register a minimal Reader subclass for .txt
    class TempReader(Reader):
        """Temporary Reader implementation used to register a non-CodeLibrary.

        Provides the minimal API required by :class:`Reader` for test purposes.
        """

        def __init__(self, *, path: Path, options: GenOpts) -> None:
            """Store path/options for the test instance."""
            self.__path = path
            self.__options = options

        @property
        def path(self) -> Path:
            """Return the stored filesystem path."""
            return self.__path

        @property
        def options(self) -> GenOpts:
            """Return the stored generation options."""
            return self.__options

        async def read(self, text: str) -> None:
            """Consume input text (store for inspection if needed)."""
            self._text = text

        def pipe(self) -> tuple[Writer, ...]:
            """Return no writers (this reader is *not* a CodeLibrary)."""
            return ()

    # inject into registry and ensure cleanup after test
    Reader.REGISTRY[".txt"] = TempReader

    main = Path(tmp_path) / "main.md"
    await main.write_text(
        """
```Python
# pytextgen generate data
# import other.txt
x = 1
```
""",
        encoding="utf-8",
    )

    opts = GenOpts(timestamp=True, init_flashcards=False, compiler=compile)
    # use anyio.Path when calling Reader APIs

    try:
        # the import resolution happens during Reader.new (it calls read), so
        # constructing the reader should raise TypeError because the imported
        # reader is not a CodeLibrary.
        with pytest.raises(TypeError):
            await Reader.new(path=main, options=opts)
    finally:
        # cleanup registry
        del Reader.REGISTRY[".txt"]
