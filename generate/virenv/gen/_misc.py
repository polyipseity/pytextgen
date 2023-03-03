# -*- coding: UTF-8 -*-
import enum as _enum
import typing as _typing


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
