# -*- coding: UTF-8 -*-
from enum import StrEnum as _StrEnum, unique as _unq
from typing import ClassVar as _ClsVar, final as _fin


@_fin
@_unq
class Tag(_StrEnum):
    __slots__: _ClsVar = ()

    CLOZE_SEPARATOR: _ClsVar = "cloze sep"
    COMMENT: _ClsVar = "cmt"
    COMMON: _ClsVar = ""
    MEMORIZE: _ClsVar = "mem"
    SEMANTICS: _ClsVar = "sem"
    SEPARATOR: _ClsVar = "sep"
    TEXT: _ClsVar = "text"
