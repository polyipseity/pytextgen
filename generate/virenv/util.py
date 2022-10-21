import abc as _abc
import io as _io
import os as _os
import pathlib as _pathlib
import types as _types
import typing as _typing

from ... import globals as _globals

_CoT = _typing.TypeVar('_CoT', covariant=True)
_CoU = _typing.TypeVar('_CoU', covariant=True)
_ExtendsUnit = _typing.TypeVar('_ExtendsUnit', bound='Unit[_typing.Any]')


@_typing.final
class Unit(_typing.Generic[_CoT]):
    __slots__ = ('__value',)

    def __init__(self: _typing.Self, value: _CoT) -> None:
        self.__value: _CoT = value

    def counit(self: _typing.Self) -> _CoT:
        return self.__value

    def bind(self: _typing.Self, func: _typing.Callable[[_CoT], _ExtendsUnit]) -> _ExtendsUnit:
        return func(self.counit())

    def extend(self: _typing.Self, func: _typing.Callable[[_typing.Self], _CoU]) -> 'Unit[_CoU]':
        return Unit(func(self))

    def map(self: _typing.Self, func: _typing.Callable[[_CoT], _CoU]) -> 'Unit[_CoU]':
        return Unit(func(self.counit()))

    def join(self: 'Unit[_ExtendsUnit]') -> _ExtendsUnit:
        return self.counit()

    def duplicate(self: _typing.Self) -> 'Unit[_typing.Self]':
        return Unit(self)


class Location(metaclass=_abc.ABCMeta):
    __slots__ = ()

    @_abc.abstractmethod
    def open(self: _typing.Self) -> _typing.TextIO: ...

    @classmethod
    def __subclasshook__(cls: type[_typing.Self], subclass: type) -> bool | _types.NotImplementedType:
        if cls is Location:
            if any(all(p not in c.__dict__ or c.__dict__[p] is None
                       for c in subclass.__mro__)
                   for p in (cls.open.__name__,)):
                return False
        return NotImplemented


@_typing.final
class PathLocation(_typing.NamedTuple):
    path: _pathlib.PurePath

    def open(self: _typing.Self) -> _typing.TextIO:
        return open(self.path, mode='r+t', **_globals.open_options)


Location.register(PathLocation)
assert issubclass(PathLocation, Location)


@_typing.final
class FileSection(_typing.NamedTuple('FileSection', path=_pathlib.PurePath, section=str)):
    __slots__ = ()

    @_typing.final
    class SectionFormat(_typing.NamedTuple):
        start: str
        stop: str
    section_formats: _typing.Mapping[str, SectionFormat] = _types.MappingProxyType({
        '': SectionFormat(
            f'[{_globals.uuid},generate,{{section}}]',
            f'[{_globals.uuid},end]'
        ),
        '.md': SectionFormat(
            f'<!--{_globals.uuid} generate section="{{section}}"-->',
            f'<!--/{_globals.uuid}-->'
        ),
    })

    path: _pathlib.PurePath
    section: str

    def open(self: _typing.Self) -> _typing.TextIO:
        if self.section:
            @_typing.final
            class IO(_io.StringIO):
                __slots__ = ('__file', '__slice')

                def __init__(self: _typing.Self, closure: FileSection, /) -> None:
                    ext: str
                    _, ext = _os.path.splitext(closure.path)
                    start_format: str = closure.section_formats[ext].start.format(
                        section=closure.section)
                    stop_format: str = closure.section_formats[ext].stop.format(
                        section=closure.section)
                    self.__file: _typing.TextIO = open(closure.path,
                                                       mode='r+t', **_globals.open_options)
                    try:
                        text: str = self.__file.read()
                        start: int = text.find(start_format)
                        if start == -1:
                            raise ValueError(f'Not found: {closure}')
                        start += len(start_format)
                        stop: int = text.find(stop_format, start)
                        if stop == -1:
                            raise ValueError(
                                f'Unenclosure from char {start}: {closure}')
                        self.__slice: slice = slice(start, stop)
                        super().__init__(text[self.__slice])
                    except BaseException as ex:
                        self.__file.close()
                        raise ex

                def close(self: _typing.Self) -> None:
                    try:
                        self.seek(0)
                        data: str = self.read()
                        with self.__file:
                            self.__file.seek(0)
                            text: str = self.__file.read()
                            self.__file.seek(0)
                            self.__file.write(''.join((
                                text[:self.__slice.start],
                                data,
                                text[self.__slice.stop:]
                            )))
                            self.__file.truncate()
                    finally:
                        super().close()
            return IO(self)
        return open(self.path, mode='r+t', **_globals.open_options)


Location.register(FileSection)
assert issubclass(FileSection, Location)
