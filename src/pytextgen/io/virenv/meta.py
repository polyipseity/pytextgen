"""Virtual environment helper exports for pytextgen.io.virenv.

This module centralizes the small package-level public surface (currently
`dirty()`) so that `__init__.py` can act as a minimal forwarder.
"""

from .config import Configuration

__all__ = ("dirty",)


def dirty() -> bool:
    """Return whether package config differs from defaults (i.e. is dirty)."""
    # Do NOT remove this import: `dirty()` must check the config state at call time, not import time, so we cannot import `CONFIG` at the module level.
    from .config import CONFIG  # noqa: PLC0415

    return CONFIG != Configuration()
