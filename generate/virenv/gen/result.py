import typing as _typing
from .... import util as _util
from .. import util as _util2


@_typing.final
class Result(_typing.NamedTuple):
    location: _util2.Location
    text: str


@_typing.final
class Results(_util.TypedTuple[Result], t_type=Result):
    pass
