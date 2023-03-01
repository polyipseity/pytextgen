# -*- coding: UTF-8 -*-
import datetime as _datetime
import re as _re
import typing as _typing

uuid: str = "08e5b0a3-f78a-46af-bf50-eb9b12f7fa1e"


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


flashcard_ease_default: int = 250
flashcard_states_format: str = "<!--SR:{states}-->"
flashcard_states_regex: _re.Pattern[str] = _re.compile(
    r"<!--SR:(.*?)-->", flags=_re.NOFLAG
)
generate_comment_format: str = "<!-- The following content is generated at {now}. Any edits will be overridden! -->"
generate_comment_regex: _re.Pattern[str] = _re.compile(
    r"^<!-- The following content is generated at (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}\+\d{2}:\d{2}). Any edits will be overridden! -->",
    flags=_re.NOFLAG,
)
assert generate_comment_regex.search(
    generate_comment_format.format(
        now=_datetime.datetime.now().astimezone().isoformat()
    )
)
open_options: _OpenOptions = _OpenOptions(
    encoding="UTF-8",
    errors="strict",
    newline=None,
)
