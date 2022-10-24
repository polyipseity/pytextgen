import abc as _abc
import os as _os
import types as _types
import typing as _typing

StrPath: _typing.TypeAlias = str | _os.PathLike[str]

_T = _typing.TypeVar('_T')


def abc_subclasshook_check(impl_cls: _abc.ABCMeta,
                           cls: _abc.ABCMeta,
                           subclass: type, /, *,
                           names: _typing.Collection[str],
                           typing: _typing.Literal['nominal',
                                                   'structural'] = 'nominal',
                           ) -> bool | _types.NotImplementedType:
    if cls is impl_cls:
        if typing == 'nominal':
            if (any(getattr(c, '__subclasshook__')(subclass) is False
                    for c in cls.__mro__ if c is not cls and hasattr(c, '__subclasshook__'))
                or any(all(c.__dict__[p] is None
                           for c in subclass.__mro__ if p in c.__dict__) for p in names)):
                return False
        elif typing == 'structural':
            if (all(getattr(c, '__subclasshook__')(subclass) is not False
                    for c in cls.__mro__ if c is not cls and hasattr(c, '__subclasshook__'))
                and all(any(c.__dict__[p] is not None
                            for c in subclass.__mro__ if p in c.__dict__) for p in names)):
                return True
        else:
            raise ValueError(typing)
    return NotImplemented


class TypedTuple(_typing.Generic[_T], tuple[_T, ...]):
    __slots__: _typing.ClassVar = ()
    element_type: type[_T]

    def __init_subclass__(cls: type[_typing.Self], element_type: type[_T], **kwargs: _typing.Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.element_type = element_type

    @_typing.overload
    def __new__(cls: type[_typing.Self], iterable: _typing.Iterable[_T], /) -> _typing.Self:
        ...

    @_typing.overload
    def __new__(cls: type[_typing.Self], *items: _T) -> _typing.Self:
        ...

    def __new__(cls: type[_typing.Self], *items: _typing.Iterable[_T] | _T) -> _typing.Self:
        if len(items) == 1 and not isinstance(items[0], cls.element_type):
            return super().__new__(cls, _typing.cast(_typing.Iterable[_T], items[0]))
        return super().__new__(cls, _typing.cast(_typing.Iterable[_T], items))

    def __repr__(self: _typing.Self) -> str:
        return type(self).__qualname__ + super().__repr__()
