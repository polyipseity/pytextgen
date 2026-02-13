"""Extra tests for `pytextgen.io.read` covering subclass hooks and import errors."""

__all__ = ()

from os import PathLike

import pytest
from anyio import Path

from pytextgen.io.options import GenOpts
from pytextgen.io.read import CodeLibrary, Reader


def test_Reader_and_CodeLibrary_subclasshook_structural():
    # create a class that *looks* like a Reader (structural)
    class FakeReader:
        @property
        def path(self):
            return None

        @property
        def options(self):
            return None

        async def read(self, text: str):
            return None

        def pipe(self):
            return ()

    # structural detection in `__subclasshook__` is conservative; ensure
    # the plain class is not treated as a Reader subclass by `issubclass`.
    assert not issubclass(FakeReader, Reader)

    # likewise a plain class that merely exposes `codes` should not be
    # recognised as a CodeLibrary by `issubclass`.
    class FakeLib:
        @property
        def codes(self) -> list[str]:
            return []

    assert not issubclass(FakeLib, CodeLibrary)


@pytest.mark.asyncio
async def test_Reader_cached_returns_same_instance(tmp_path: PathLike[str]):
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
