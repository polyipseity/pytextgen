import typing as _typing
from .. import util as _util


@_typing.final
class Result(_typing.NamedTuple):
    location: _util.Location
    text: str


@_typing.final
class Results(tuple[Result, ...]):
    @_typing.overload
    def __new__(cls: type[_typing.Self], iterable: _typing.Iterable[Result], /) -> _typing.Self:
        ...

    @_typing.overload
    def __new__(cls: type[_typing.Self], *items: Result) -> _typing.Self:
        ...

    def __new__(cls: type[_typing.Self], *items: _typing.Iterable[Result] | Result) -> _typing.Self:
        if len(items) == 1 and not isinstance(items[0], Result):
            return super().__new__(cls, items[0])
        return super().__new__(cls, _typing.cast(_typing.Iterable[Result], items))
