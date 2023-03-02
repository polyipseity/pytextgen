# -*- coding: UTF-8 -*-
import datetime as _datetime
import re as _re
import typing as _typing

UUID = "08e5b0a3-f78a-46af-bf50-eb9b12f7fa1e"


@_typing.final
class _OpenOptions(_typing.TypedDict):
    encoding: str
    errors: _typing.Literal[
        "strict",
        "ignore",
        "replace",
        "surrogateescape",
        "xmlcharrefreplace",
        "backslashreplace",
        "namereplace",
    ]
    newline: None | _typing.Literal["", "\n", "\r", "\r\n"]


FLASHCARD_EASE_DEFAULT = 250
FLASHCARD_STATES_FORMAT = "<!--SR:{states}-->"
FLASHCARD_STATES_REGEX = _re.compile(r"<!--SR:(.*?)-->", flags=_re.NOFLAG)
GENERATE_COMMENT_FORMAT = "<!-- The following content is generated at {now}. Any edits will be overridden! -->"
GENERATE_COMMENT_REGEX = _re.compile(
    r"^<!-- The following content is generated at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}). Any edits will be overridden! -->",
    flags=_re.NOFLAG,
)
assert GENERATE_COMMENT_REGEX.search(
    GENERATE_COMMENT_FORMAT.format(
        now=_datetime.datetime.now().astimezone().isoformat()
    )
)
OPEN_OPTIONS = _OpenOptions(
    encoding="UTF-8",
    errors="strict",
    newline=None,
)
