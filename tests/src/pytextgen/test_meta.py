"""Tests that the package version defined in pyproject.toml matches the `VERSION`
constant defined in `src/pytextgen/meta.py`.

This test reads `pyproject.toml` using `tomllib` and imports the package
module to assert the two version values are equal.
"""

import importlib.util
import tomllib

import pytest
from anyio import Path

from pytextgen.meta import OPEN_TEXT_OPTIONS

__all__ = ()


@pytest.mark.asyncio
async def test_pyproject_and_init_version_match():
    """Ensure [project].version in pyproject.toml equals `src/pytextgen/meta.py::VERSION`.

    This test loads the project metadata from the TOML file and imports the
    package module to compare versions.
    """
    pyproject_text = await Path("pyproject.toml").read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)
    assert "project" in pyproject and "version" in pyproject["project"], (
        "pyproject.toml is missing [project].version"
    )
    py_version = pyproject["project"]["version"]

    meta_path = Path("src/pytextgen/meta.py")
    spec = importlib.util.spec_from_file_location("pytextgen.meta", meta_path)
    assert spec is not None and spec.loader is not None, (
        f"Could not load module from {meta_path}"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "VERSION"), "Could not find VERSION in src/pytextgen/meta.py"
    meta_version = module.VERSION

    assert py_version == meta_version, (
        f"Version mismatch: pyproject.toml has {py_version!r} but src/pytextgen/meta.py has {meta_version!r}"
    )


def test_open_text_options_shape():
    """OPEN_TEXT_OPTIONS exposes a mapping suitable for file open calls."""
    assert isinstance(OPEN_TEXT_OPTIONS, dict)
    assert OPEN_TEXT_OPTIONS["encoding"] == "UTF-8"
