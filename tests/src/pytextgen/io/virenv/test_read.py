"""Tests for :mod:`pytextgen.io.virenv.read`."""

from os import PathLike
from typing import cast

import pytest
from anyio import Path

from pytextgen.io.utils import Location, PathLocation
from pytextgen.io.virenv.read import read_flashcard_states

"""Public symbols exported by this test module (none)."""
__all__ = ()


@pytest.mark.anyio
async def test_read_flashcard_states_from_string() -> None:
    """String input should be parsed into one or more flashcard state groups."""
    text = "<!--SR:!2024-01-02,1,250-->"
    groups = list(await read_flashcard_states(text))

    assert len(groups) == 1
    assert len(groups[0]) == 1
    assert str(groups[0][0]) == "!2024-01-02,1,250"


@pytest.mark.anyio
async def test_read_flashcard_states_from_location(tmp_path: PathLike[str]) -> None:
    """Location input should be read and parsed equivalently to text input."""
    path = Path(tmp_path) / "states.md"
    await path.write_text("<!--SR:!2024-02-03,2,260-->", encoding="utf-8")

    groups = list(await read_flashcard_states(cast(Location, PathLocation(path=path))))

    assert len(groups) == 1
    assert len(groups[0]) == 1
    state = groups[0][0]
    assert state.interval == 2
    assert state.ease == 260


@pytest.mark.anyio
async def test_read_flashcard_states_without_markers_returns_empty() -> None:
    """Input with no flashcard-state markers should return an empty iterator."""
    assert list(await read_flashcard_states("no markers")) == []
