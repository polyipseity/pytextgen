# -*- coding: UTF-8 -*-
from datetime import datetime as _dt
from logging import getLogger as _getLogger
from re import NOFLAG as _NOFLAG, compile as _re_comp
from typing import Literal as _Lit, TypedDict as _TDict, final as _fin


@_fin
class _OpenOptions(_TDict):
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
VERSION = "6.7.1"

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
