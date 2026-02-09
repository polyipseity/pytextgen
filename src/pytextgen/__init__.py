"""Top-level package metadata and shared constants for pytextgen.

This module exposes the package `NAME`, `VERSION` and several common
formats and regular expressions used across the package.
"""

from datetime import datetime as _dt
from logging import getLogger as _getLogger
from re import NOFLAG as _NOFLAG
from re import compile as _re_comp
from typing import Literal as _Lit
from typing import TypedDict as _TDict
from typing import final as _fin

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


@_fin
class _OpenOptions(_TDict):
    """Typed dict describing options used when opening text files.

    Matches the arguments accepted by `open(..., encoding=..., errors=..., newline=...)`.
    """

    encoding: str
    errors: _Lit[
        "strict",
        "ignore",
        "replace",
        "surrogateescape",
        "xmlcharrefreplace",
        "backslashreplace",
        "namereplace",
    ]
    newline: _Lit["", "\n", "\r", "\r\n"] | None


# update `pyproject.toml`
NAME = "pytextgen"
VERSION = "7.0.0"

FLASHCARD_EASE_DEFAULT = 250
FLASHCARD_STATES_FORMAT = "<!--SR:{states}-->"
FLASHCARD_STATES_REGEX = _re_comp(r"<!--SR:(.*?)-->", _NOFLAG)
GENERATE_COMMENT_FORMAT = "<!-- The following content is generated at {now}. Any edits will be overridden! -->"
GENERATE_COMMENT_REGEX = _re_comp(
    r"^<!-- The following content is generated at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}). Any edits will be overridden! -->",
    _NOFLAG,
)
assert GENERATE_COMMENT_REGEX.search(
    GENERATE_COMMENT_FORMAT.format(now=_dt.now().astimezone().isoformat())
)

LOGGER = _getLogger(NAME)
OPEN_TEXT_OPTIONS = _OpenOptions(
    encoding="UTF-8",
    errors="strict",
    newline=None,
)
UUID = "08e5b0a3-f78a-46af-bf50-eb9b12f7fa1e"
