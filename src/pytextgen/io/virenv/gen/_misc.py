"""Small enums used by text code generation and templating."""

from enum import StrEnum, unique
from typing import ClassVar, final

__all__ = ("Tag",)


@final
@unique
class Tag(StrEnum):
    """Tag values used by `TextCode` based helpers."""

    __slots__: ClassVar = ()

    CLOZE_SEPARATOR = "cloze sep"
    COMMENT = "cmt"
    COMMON = ""
    MEMORIZE = "mem"
    SEMANTICS = "sem"
    SEPARATOR = "sep"
    TEXT = "text"
