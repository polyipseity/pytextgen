"""Virtual environment helpers for safely executing code fragments.

This package contains utilities for flashcards, code generation helpers,
and config used by the execution environment.
"""

from .config import CONFIG as _CONFIG
from .config import Configuration as _Configuration

__all__ = ("dirty",)


def dirty() -> bool:
    """Return whether package config differs from defaults (i.e. is dirty)."""
    return _CONFIG != _Configuration()
