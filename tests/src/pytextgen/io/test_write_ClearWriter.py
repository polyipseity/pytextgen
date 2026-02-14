"""Tests for `pytextgen.io.write.ClearWriter` behaviour."""

from datetime import datetime
from os import PathLike

import pytest
from anyio import Path

from pytextgen.io.options import ClearOpts, ClearType
from pytextgen.io.write import ClearWriter
from pytextgen.meta import GENERATE_COMMENT_FORMAT, GENERATE_COMMENT_REGEX

__all__ = ()


@pytest.mark.asyncio
async def test_ClearWriter_truncates_content_sections(tmp_path: PathLike[str]):
    """ClearWriter clears content sections while retaining section markers."""
    f = Path(tmp_path) / "doc.md"
    await f.write_text(
        """
<!--pytextgen generate section="s"-->
SOME GENERATED
<!--/pytextgen-->
""",
        encoding="utf-8",
    )

    opts = ClearOpts(types={ClearType.CONTENT})
    async with ClearWriter(f, options=opts).write():
        pass

    text = await f.read_text(encoding="utf-8")
    # section should remain but have empty body
    assert "SOME GENERATED" not in text


@pytest.mark.asyncio
async def test_ClearWriter_strips_flashcard_state(tmp_path: PathLike[str]):
    """ClearWriter strips flashcard state entries when requested."""
    f = Path(tmp_path) / "doc2.md"
    await f.write_text(
        """
<!--pytextgen generate section="s"-->
Some text <!--SR:!2023-01-02,5,250--> more
<!--/pytextgen-->
""",
        encoding="utf-8",
    )

    opts = ClearOpts(types={ClearType.FLASHCARD_STATE})
    async with ClearWriter(f, options=opts).write():
        pass

    text = await f.read_text(encoding="utf-8")
    assert "<!--SR:" not in text


@pytest.mark.asyncio
async def test_ClearWriter_removes_generated_timestamp_on_content_clear(
    tmp_path: PathLike[str],
):
    """Clearing content removes the generated timestamp header."""
    f = Path(tmp_path) / "doc_ts.md"
    # section contains a generated comment header followed by content
    header = GENERATE_COMMENT_FORMAT.format(now=datetime.now().astimezone().isoformat())
    await f.write_text(
        f"""
<!--pytextgen generate section="s"-->
{header}payload
<!--/pytextgen-->
""",
        encoding="utf-8",
    )

    opts = ClearOpts(types={ClearType.CONTENT})
    async with ClearWriter(f, options=opts).write():
        pass

    text = await f.read_text(encoding="utf-8")
    # the generated header must be removed when the section is cleared
    assert GENERATE_COMMENT_REGEX.search(text) is None


@pytest.mark.asyncio
async def test_ClearWriter_does_not_insert_generated_timestamp(tmp_path: PathLike[str]):
    """Clearing flashcard state does not insert a generated timestamp."""
    f = Path(tmp_path) / "doc_no_ts.md"
    await f.write_text(
        """
<!--pytextgen generate section=\"s\"-->
existing
<!--/pytextgen-->
""",
        encoding="utf-8",
    )

    opts = ClearOpts(types={ClearType.FLASHCARD_STATE})
    async with ClearWriter(f, options=opts).write():
        pass

    text = await f.read_text(encoding="utf-8")
    # ClearWriter should not add a generated comment when stripping flashcard state
    assert GENERATE_COMMENT_REGEX.search(text) is None
