"""Tests for `src/pytextgen/utils.py` (CompileCache).

These tests mirror the package source layout: `src/pytextgen/utils.py` →
`tests/src/pytextgen/test_utils.py`.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from pytextgen.utils import CompileCache

__all__ = ()


@pytest.mark.asyncio
async def test_CompileCache_metadata_roundtrip(tmp_path: Path):
    folder = tmp_path / "cache"
    async with CompileCache(folder=folder) as cache:
        code = cache.compile("a=1\n", filename="test", mode="exec")
        assert hasattr(code, "co_code")

    md = folder / "metadata.json"
    assert md.exists()
    data = json.loads(md.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    data: list[Any] = data  # For type checking
    assert len(data) >= 1
    entry = data[0]
    assert "key" in entry and "value" in entry
    key = entry["key"]
    assert "source" in key and "filename" in key
