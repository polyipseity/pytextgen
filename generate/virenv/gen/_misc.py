# -*- coding: UTF-8 -*-
import enum as _enum
import re as _re
import regex as _regex
import sys as _sys
import typing as _typing
import unicodedata as _unicodedata

_punctuations: _typing.Collection[str] = tuple(
    chr(char)
    for char in range(_sys.maxunicode)
    if _unicodedata.category(chr(char)).startswith("P")
)
_punctuation_regex: _regex.Pattern[str] = _regex.compile(
    r"(?<={delims})(?<!^(?:{delims})+)(?!$|{delims})".format(
        delims=r"|".join(map(_re.escape, _punctuations))
    ),
    flags=_regex.VERSION0,
)


@_typing.final
@_enum.unique
class Tag(_enum.StrEnum):
    __slots__: _typing.ClassVar = ()

    COMMON: _typing.ClassVar = ""
    COMMENT: _typing.ClassVar = "cmt"
    TEXT: _typing.ClassVar = "text"
    MEMORIZE: _typing.ClassVar = "mem"
    SEMANTICS: _typing.ClassVar = "sem"
    CLOZE_SEPARATOR: _typing.ClassVar = "cloze sep"


def affix_lines(text: str, /, *, prefix: str = "", suffix: str = "") -> str:
    def ret_gen() -> _typing.Iterator[str]:
        newline: str = ""
        for line in text.splitlines():
            yield newline
            yield prefix
            yield line
            yield suffix
            newline = "\n"

    return "".join(ret_gen())


def strip_lines(text: str, /, *, chars: str | None = None) -> str:
    return "\n".join(line.strip(chars) for line in text.splitlines())


def split_by_punctuations(text: str) -> _typing.Iterator[str]:
    return _punctuation_regex.splititer(text)
