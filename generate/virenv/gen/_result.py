# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import typing as _typing

from ..util import Location as _Loc, TypedTuple as _TTuple


@_typing.final
@_dataclasses.dataclass(
    init=True,
    repr=True,
    eq=True,
    order=False,
    unsafe_hash=False,
    frozen=True,
    match_args=True,
    kw_only=True,
    slots=True,
)
class Result:
    location: _Loc
    text: str


@_typing.final
class Results(_TTuple[Result], element_type=Result):
    __slots__: _typing.ClassVar = ()
