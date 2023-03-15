# -*- coding: UTF-8 -*-
import enum as _enum
import typing as _typing


@_typing.final
@_enum.unique
class Tag(_enum.StrEnum):
    __slots__: _typing.ClassVar = ()

    CLOZE_SEPARATOR: _typing.ClassVar = "cloze sep"
    COMMENT: _typing.ClassVar = "cmt"
    COMMON: _typing.ClassVar = ""
    MEMORIZE: _typing.ClassVar = "mem"
    SEMANTICS: _typing.ClassVar = "sem"
    SEPARATOR: _typing.ClassVar = "sep"
    TEXT: _typing.ClassVar = "text"
