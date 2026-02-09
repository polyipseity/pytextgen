"""Virtual environment helpers for safely executing code fragments.

This package contains utilities for flashcards, code generation helpers,
and config used by the execution environment.
"""

from . import config as config
from . import gen as gen
from . import read as read
from . import util as util

__all__ = ("config", "gen", "read", "util", "dirty")


def dirty() -> bool:
    """Return whether package config differs from defaults (i.e. is dirty)."""
    # Use the `config` module imported at package level to avoid re-importing.
    return config.CONFIG != config.Configuration()
