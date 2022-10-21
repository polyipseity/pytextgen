import os as _os
import typing as _typing

StrPath: _typing.TypeAlias = str | _os.PathLike[str]

_T = _typing.TypeVar('_T')


class TypedTuple(_typing.Generic[_T], tuple[_T, ...]):
    __t_type: type[_T]

    def __init_subclass__(cls, t_type: type[_T], **kwargs: _typing.Any) -> None:
        cls.__t_type = t_type
        return super().__init_subclass__(**kwargs)

    @_typing.overload
    def __new__(cls: type[_typing.Self], iterable: _typing.Iterable[_T], /) -> _typing.Self:
        ...

    @_typing.overload
    def __new__(cls: type[_typing.Self], *items: _T) -> _typing.Self:
        ...

    def __new__(cls: type[_typing.Self], *items: _typing.Iterable[_T] | _T) -> _typing.Self:
        if len(items) == 1 and not isinstance(items[0], cls.__t_type):
            return super().__new__(cls, _typing.cast(_typing.Iterable[_T], items[0]))
        return super().__new__(cls, _typing.cast(_typing.Iterable[_T], items))

    def __repr__(self: _typing.Self) -> str:
        return type(self).__qualname__ + super().__repr__()
