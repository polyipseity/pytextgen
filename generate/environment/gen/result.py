import typing as _typing
from .. import util as _util


@_typing.final
class Result:
    __slots__ = ('__location', '__text')

    def __init__(self: _typing.Self, *,
                 location: _util.Location,
                 text: str) -> None:
        self.__location: _util.Location = location
        self.__text: str = text

    def __repr__(self: _typing.Self) -> str:
        return f'{Result.__qualname__}(location={self.__location!r}, text={self.__text!r})'

    @property
    def location(self: _typing.Self) -> _util.Location: return self.__location

    @property
    def text(self: _typing.Self) -> str: return self.__text


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
