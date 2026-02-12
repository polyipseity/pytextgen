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

__all__ = (
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
NAME = "pytextgen"
VERSION = "7.0.0"

FLASHCARD_EASE_DEFAULT = 250
FLASHCARD_STATES_FORMAT = "<!--SR:{states}-->"
FLASHCARD_STATES_REGEX = re.compile(r"<!--SR:(.*?)-->", re.NOFLAG)
GENERATE_COMMENT_FORMAT = "<!-- The following content is generated at {now}. Any edits will be overridden! -->"
GENERATE_COMMENT_REGEX = re.compile(
    r"^<!-- The following content is generated at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}). Any edits will be overridden! -->",
    re.NOFLAG,
)
assert GENERATE_COMMENT_REGEX.search(
    GENERATE_COMMENT_FORMAT.format(now=datetime.now().astimezone().isoformat())
)

LOGGER = getLogger(NAME)
OPEN_TEXT_OPTIONS = _OpenOptions(
    encoding="UTF-8",
    errors="strict",
    newline=None,
)
UUID = "08e5b0a3-f78a-46af-bf50-eb9b12f7fa1e"
