from enum import StrEnum as _StrEnum
from enum import unique as _unq
from typing import ClassVar as _ClsVar
from typing import final as _fin

__all__ = ("Tag",)


@_fin
@_unq
class Tag(_StrEnum):
    __slots__: _ClsVar = ()

    CLOZE_SEPARATOR = "cloze sep"
    COMMENT = "cmt"
    COMMON = ""
    MEMORIZE = "mem"
    SEMANTICS = "sem"
    SEPARATOR = "sep"
    TEXT = "text"
