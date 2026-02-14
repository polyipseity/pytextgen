"""Extra tests for `pytextgen.io.read` covering subclass hooks and import errors."""

from os import PathLike

import pytest
from anyio import Path

from pytextgen.io.options import GenOpts
from pytextgen.io.read import CodeLibrary, Reader

__all__ = ()


def test_Reader_and_CodeLibrary_subclasshook_structural():
    """`issubclass` structural checks for Reader/CodeLibrary behave correctly."""

    # create a class that *looks* like a Reader (structural)
    class FakeReader:
        """Minimal class exposing the Reader-shaped attributes for structural tests."""

        @property
        def path(self):
            """Return a dummy path (None).'"""
            return None

        @property
        def options(self):
            """Return a dummy options value (None)."""
            return None

        async def read(self, text: str):
            """Async placeholder for Reader.read used in structural checks."""
            return None

        def pipe(self):
            """Return an empty collection as a Reader.pipe placeholder."""
            return ()

    # structural detection in `__subclasshook__` is conservative; ensure
    # the plain class is not treated as a Reader subclass by `issubclass`.
    assert not issubclass(FakeReader, Reader)

    # likewise a plain class that merely exposes `codes` should not be
    # recognised as a CodeLibrary by `issubclass`.
    class FakeLib:
        """Minimal type exposing a ``codes`` property for CodeLibrary checks."""

        @property
        def codes(self) -> list[str]:
            """Return an empty list of codes for the structural test."""
            return []

    assert not issubclass(FakeLib, CodeLibrary)


@pytest.mark.asyncio
async def test_Reader_cached_returns_same_instance(tmp_path: PathLike[str]):
    """`Reader.cached` returns the same instance for the same path/options."""
    f = Path(tmp_path) / "f.md"
    await f.write_text(
        """
```Python
# pytextgen generate data
x = 1
```
""",
        encoding="utf-8",
    )
    opts = GenOpts(timestamp=True, init_flashcards=False, compiler=compile)

    r1 = await Reader.cached(path=f, options=opts)
    r2 = await Reader.cached(path=f, options=opts)
    assert r1 is r2
