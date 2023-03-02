# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import typing as _typing

from ..util import Location, TypedTuple


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
    location: Location
    text: str


@_typing.final
class Results(TypedTuple[Result], element_type=Result):
    __slots__: _typing.ClassVar = ()
