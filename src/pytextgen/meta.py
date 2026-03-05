"""Package-level metadata and shared constants for pytextgen.

This module contains the canonical package constants and values which are
forwarded from `src/pytextgen/__init__.py`. The new convention is to keep
`__init__.py` minimal and centralize exported symbols in `meta.py` so that
package-level exports are explicit, easy to test, and reduce import-time
costs and accidental cycles.
"""

import re
from datetime import datetime
from logging import getLogger
from typing import Literal, TypedDict, final

"""Public symbols exported by this module."""
__all__ = (
    "MAX_CONCURRENT_FILE_OPERATIONS",
    "NAME",
    "VERSION",
    "FLASHCARD_EASE_DEFAULT",
    "FLASHCARD_STATES_FORMAT",
    "FLASHCARD_STATES_REGEX",
    "GENERATE_COMMENT_FORMAT",
    "GENERATE_COMMENT_REGEX",
    "LOGGER",
    "OPEN_TEXT_OPTIONS",
    "UUID",
)

"""Maximum concurrent file operations to avoid exhausting file descriptors."""
MAX_CONCURRENT_FILE_OPERATIONS = 256


@final
class _OpenOptions(TypedDict):
    """Typed dict describing options used when opening text files.

    Matches the arguments accepted by `open(..., encoding=..., errors=..., newline=...)`.
    """

    encoding: str
    errors: Literal[
        "strict",
        "ignore",
        "replace",
        "surrogateescape",
        "xmlcharrefreplace",
        "backslashreplace",
        "namereplace",
    ]
    newline: Literal["", "\n", "\r", "\r\n"] | None


# update `pyproject.toml`
"""Package display name."""
NAME = "pytextgen"
"""Package version (keep in sync with pyproject.toml)."""
VERSION = "8.1.0"

"""Default ease factor for generated flashcards."""
FLASHCARD_EASE_DEFAULT = 250
"""Format string for flashcard state comments."""
FLASHCARD_STATES_FORMAT = "<!--SR:{states}-->"
"""Regex to parse flashcard state comments."""
FLASHCARD_STATES_REGEX = re.compile(r"<!--SR:(.*?)-->", re.NOFLAG)
"""Format string for the generate-block marker comment."""
GENERATE_COMMENT_FORMAT = "<!-- The following content is generated at {now}. Any edits will be overridden! -->"
"""Regex to match and parse the generate-block marker comment."""
GENERATE_COMMENT_REGEX = re.compile(
    r"^<!-- The following content is generated at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}). Any edits will be overridden! -->",
    re.NOFLAG,
)
assert GENERATE_COMMENT_REGEX.search(
    GENERATE_COMMENT_FORMAT.format(now=datetime.now().astimezone().isoformat())
)

"""Package-level logger."""
LOGGER = getLogger(NAME)
# keep exported `OPEN_TEXT_OPTIONS` as a plain dict for `**`-unpacking
"""Default options for opening text files (encoding, errors, newline)."""
OPEN_TEXT_OPTIONS = _OpenOptions(
    encoding="UTF-8",
    errors="strict",
    newline=None,
)
"""Fixed UUID used for deterministic generation markers."""
UUID = "08e5b0a3-f78a-46af-bf50-eb9b12f7fa1e"
