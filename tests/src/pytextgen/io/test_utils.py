"""Tests for :mod:`pytextgen.io.utils` (Location, FileSection, Result)."""

from os import PathLike

import pytest
from anyio import Path

from pytextgen.io.utils import (
    NULL_LOCATION,
    FileSection,
    NullLocation,
    PathLocation,
    Result,
)
from pytextgen.utils import wrap_async

"""Public symbols exported by this module (none)."""
__all__ = ()


def test_result_isinstance_guard() -> None:
    """`Result.isinstance` returns True for matching shape and False otherwise."""
    r = Result(location=NULL_LOCATION, text="hello")
    assert Result.isinstance(r)

    class Bad:
        """Type intentionally not matching ``Result`` shape for negative test."""

        pass

    assert not Result.isinstance(Bad())


@pytest.mark.anyio
async def test_NullLocation_open_uses_in_memory_text_buffer() -> None:
    """`NullLocation.open` should return an in-memory read/write buffer."""
    loc = NullLocation()
    assert loc.path is None

    async with loc.open() as io:
        await wrap_async(io.write("abc"))
        await wrap_async(io.seek(0))
        assert await wrap_async(io.read()) == "abc"


@pytest.mark.anyio
async def test_PathLocation_open_roundtrip(tmp_path: PathLike[str]) -> None:
    """`PathLocation.open` should read/write the referenced file path."""
    path = Path(tmp_path) / "path_location.txt"
    await path.write_text("seed", encoding="utf-8")

    loc = PathLocation(path=path)
    assert loc.path == path

    async with loc.open() as io:
        assert await wrap_async(io.read()) == "seed"
        await wrap_async(io.seek(0))
        await wrap_async(io.write("grown"))
        await wrap_async(io.truncate())

    assert await path.read_text(encoding="utf-8") == "grown"


@pytest.mark.anyio
async def test_FileSection_find_and_open_updates_target_section(
    tmp_path: PathLike[str],
) -> None:
    """Finding and editing a markdown section should update only that section."""
    path = Path(tmp_path) / "doc.md"
    await path.write_text(
        "\n".join(
            (
                "prefix",
                '<!--pytextgen generate section="alpha"-->',
                "OLD",
                "<!--/pytextgen-->",
                "suffix",
            )
        ),
        encoding="utf-8",
    )

    sections = tuple(await FileSection.find(path))
    assert sections == ("alpha",)

    async with FileSection(path=path, section="alpha").open() as io:
        assert await wrap_async(io.read()) == "\nOLD\n"
        await wrap_async(io.seek(0))
        await wrap_async(io.write("\nNEW\n"))
        await wrap_async(io.truncate())

    text = await path.read_text(encoding="utf-8")
    assert "NEW" in text
    assert "OLD" not in text
    assert text.startswith("prefix")
    assert text.endswith("suffix")


@pytest.mark.anyio
async def test_FileSection_empty_section_opens_whole_file(
    tmp_path: PathLike[str],
) -> None:
    """A blank section name should fall back to full-file read/write access."""
    path = Path(tmp_path) / "whole.md"
    await path.write_text("whole", encoding="utf-8")

    async with FileSection(path=path, section="").open() as io:
        assert await wrap_async(io.read()) == "whole"
        await wrap_async(io.seek(0))
        await wrap_async(io.write("whole-updated"))
        await wrap_async(io.truncate())

    assert await path.read_text(encoding="utf-8") == "whole-updated"


@pytest.mark.anyio
async def test_FileSection_find_unknown_extension_raises(
    tmp_path: PathLike[str],
) -> None:
    """Unknown file extensions should raise ValueError with helpful context."""
    path = Path(tmp_path) / "doc.txt"
    await path.write_text("irrelevant", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown extension"):
        await FileSection.find(path)


@pytest.mark.anyio
async def test_FileSection_find_duplicate_sections_raise(
    tmp_path: PathLike[str],
) -> None:
    """Duplicate section names should raise ValueError with section details."""
    path = Path(tmp_path) / "dup.md"
    await path.write_text(
        "\n".join(
            (
                '<!--pytextgen generate section="dup"-->',
                "a",
                "<!--/pytextgen-->",
                '<!--pytextgen generate section="dup"-->',
                "b",
                "<!--/pytextgen-->",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match='Duplicated section "dup"'):
        await FileSection.find(path)


@pytest.mark.anyio
async def test_FileSection_find_unenclosed_section_raises(
    tmp_path: PathLike[str],
) -> None:
    """Missing closing marker should raise ValueError with location details."""
    path = Path(tmp_path) / "unclosed.md"
    await path.write_text(
        "\n".join(
            (
                '<!--pytextgen generate section="alpha"-->',
                "body",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unenclosure from char"):
        await FileSection.find(path)


@pytest.mark.anyio
async def test_FileSection_find_too_many_closings_raises(
    tmp_path: PathLike[str],
) -> None:
    """Extra closing markers should raise ValueError for malformed content."""
    path = Path(tmp_path) / "extra_close.md"
    await path.write_text("<!--/pytextgen-->", encoding="utf-8")

    with pytest.raises(ValueError, match="Too many closings at char"):
        await FileSection.find(path)
