"""Top-level package: intentionally minimal and non-exporting.

Per repository convention, package-level constants and stable public surface
are defined in `pytextgen.meta`. This top-level `__init__` intentionally
exports only a minimal public version symbol for runtime metadata access.
"""

from .meta import VERSION as __version__

"""Public symbols exported by this module."""
__all__ = ("__version__",)
