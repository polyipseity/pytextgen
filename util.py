import abc as _abc
import os as _os
import types as _types
import typing as _typing

_T = _typing.TypeVar('_T')
_T_co = _typing.TypeVar('_T_co', covariant=True)
_T1_co = _typing.TypeVar('_T1_co', covariant=True)
_ExtendsUnit = _typing.TypeVar('_ExtendsUnit', bound='Unit[_typing.Any]')

StrPath: _typing.TypeAlias = str | _os.PathLike[str]


def identity(var: _T) -> _T:
    return var


def constant(var: _T) -> _typing.Callable[..., _T]:
    def func(*_: _typing.Any) -> _T:
        return var
    return func


def tuple1(var: _T) -> tuple[_T]:
    return (var,)


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


@_typing.final
class Unit(_typing.Generic[_T_co]):
    __slots__: _typing.ClassVar = ('__value',)

    def __init__(self: _typing.Self, value: _T_co) -> None:
        self.__value: _T_co = value

    def counit(self: _typing.Self) -> _T_co:
        return self.__value

    def bind(self: _typing.Self, func: _typing.Callable[[_T_co], _ExtendsUnit]) -> _ExtendsUnit:
        return func(self.counit())

    def extend(self: _typing.Self, func: _typing.Callable[[_typing.Self], _T1_co]) -> 'Unit[_T1_co]':
        return Unit(func(self))

    def map(self: _typing.Self, func: _typing.Callable[[_T_co], _T1_co]) -> 'Unit[_T1_co]':
        return Unit(func(self.counit()))

    def join(self: 'Unit[_ExtendsUnit]') -> _ExtendsUnit:
        return self.counit()

    def duplicate(self: _typing.Self) -> 'Unit[_typing.Self]':
        return Unit(self)


class TypedTuple(_typing.Generic[_T], tuple[_T, ...]):
    __slots__: _typing.ClassVar = ()
    element_type: type[_T]

    def __init_subclass__(cls: type[_typing.Self], element_type: type[_T], **kwargs: _typing.Any | None) -> None:
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
