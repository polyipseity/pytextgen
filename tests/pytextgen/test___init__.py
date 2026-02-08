"""Tests that the package version defined in pyproject.toml matches the `VERSION`
constant defined in `src/pytextgen/__init__.py`.

This test reads `pyproject.toml` using `tomllib` and imports the package
module to assert the two version values are equal.
"""

import importlib.util
import tomllib
from pathlib import Path

__all__ = ()


def test_pyproject_and_init_version_match():
    """Ensure [project].version in pyproject.toml equals src/pytextgen.VERSION.

    This test loads the project metadata from the TOML file and imports the
    package module to compare versions.
    """
    pyproject_text = Path("pyproject.toml").read_text(encoding="utf-8")
    pyproject = tomllib.loads(pyproject_text)
    assert "project" in pyproject and "version" in pyproject["project"], (
        "pyproject.toml is missing [project].version"
    )
    py_version = pyproject["project"]["version"]

    init_path = Path("src/pytextgen/__init__.py")
    spec = importlib.util.spec_from_file_location("pytextgen", str(init_path))
    assert spec is not None and spec.loader is not None, (
        f"Could not load module from {init_path}"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "VERSION"), (
        "Could not find VERSION in src/pytextgen/__init__.py"
    )
    init_version = module.VERSION

    assert py_version == init_version, (
        f"Version mismatch: pyproject.toml has {py_version!r} but src/pytextgen/__init__.py has {init_version!r}"
    )
