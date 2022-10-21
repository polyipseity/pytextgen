import abc as _abc
import collections.abc as _collections_abc
import datetime as _datetime
import io as _io
import os as _os
import pathlib as _pathlib
import re as _re
import types as _types
import typing as _typing

from ... import globals as _globals
from ... import util as _util

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
    path: _pathlib.Path

    def open(self: _typing.Self) -> _typing.TextIO:
        return open(self.path, mode='r+t', **_globals.open_options)


Location.register(PathLocation)
assert issubclass(PathLocation, Location)


@_typing.final
class FileSection(_typing.NamedTuple('FileSection', path=_pathlib.Path, section=str)):
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

    path: _pathlib.Path
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
                    except Exception as ex:
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


class FlashcardGroup(_typing.Sequence[str]):
    __slots__ = ()

    @_abc.abstractmethod
    def __str__(self: _typing.Self) -> str: ...

    @classmethod
    def __subclasshook__(cls: type[_typing.Self], subclass: type) -> bool | _types.NotImplementedType:
        if cls is FlashcardGroup:
            if any(getattr(c, '__subclasshook__')(subclass) is False
                   for c in cls.__mro__ if c is not cls and hasattr(c, '__subclasshook__'))\
                or any(all(p not in c.__dict__ or c.__dict__[p] is None
                       for c in subclass.__mro__)
                       for p in (cls.__str__.__name__,)):
                return False
        return NotImplemented


@_typing.final
class TwoSidedFlashcard(_typing.NamedTuple('Flashcard', left=str, right=str, reversible=bool)):
    __slots__ = ()

    @_typing.final
    class SeparatorKey(_typing.NamedTuple):
        reversible: bool
        multiline: bool
    separators: _typing.Mapping[SeparatorKey, str] = _types.MappingProxyType({
        SeparatorKey(reversible=False, multiline=False): '::',
        SeparatorKey(reversible=True, multiline=False): ':::',
        SeparatorKey(reversible=False, multiline=True): '\n??\n',
        SeparatorKey(reversible=True, multiline=True): '\n???\n',
    })

    left: str
    right: str
    reversible: bool

    def __len__(self: _typing.Self) -> int:
        return 2 if self.reversible else 1

    def __getitem__(self: _typing.Self, index: int) -> str:
        if self.reversible:
            if -2 > index or index >= 2:
                raise IndexError(index)
        elif -1 > index or index >= 1:
            raise IndexError(index)
        return str(self)

    def __str__(self: _typing.Self) -> str:
        return self.separators[self.SeparatorKey(
            reversible=self.reversible,
            multiline='\n' in self.left or '\n' in self.right
        )].join((self.left, self.right))


FlashcardGroup.register(TwoSidedFlashcard)
assert issubclass(TwoSidedFlashcard, FlashcardGroup)


@_typing.final
class FlashcardState(_typing.NamedTuple('FlashcardState', date=_datetime.date, interval=int, ease=int)):
    __slots__ = ()
    format: str = '!{date},{interval},{ease}'
    regex: _re.Pattern[str] = _re.compile(
        r'!(\d{4}-\d{2}-\d{2}),(\d+),(\d+)',
        flags=0
    )

    date: _datetime.date
    interval: int
    ease: int

    def __str__(self: _typing.Self) -> str:
        return self.format.format(date=self.date, interval=self.interval, ease=self.ease)

    @classmethod
    def compile_many(cls: type[_typing.Self], text: str) -> _typing.Iterator[_typing.Self]:
        match: _re.Match[str]
        for match in cls.regex.finditer(text):
            yield cls(
                date=_datetime.date.fromisoformat(match.group(1)),
                interval=int(match.group(2)),
                ease=int(match.group(3)),
            )

    @classmethod
    def compile(cls: type[_typing.Self], text: str) -> _typing.Self:
        rets: _typing.Iterator[_typing.Self] = cls.compile_many(text)
        try:
            ret: _typing.Self = next(rets)
        except StopIteration as ex:
            raise ValueError(f'No matches: {text}') from ex
        try:
            next(rets)
            raise ValueError(f'Too many matches: {text}')
        except StopIteration:
            pass
        return ret


@_typing.final
class FlashcardStateGroup(_util.TypedTuple[FlashcardState], element_type=FlashcardState):
    __slots__ = ()
    format: str = '<!--SR:{states}-->'
    regex: _re.Pattern[str] = _re.compile(r'<!--SR:(.*?)-->', flags=0)

    def __str__(self: _typing.Self) -> str:
        if self:
            return self.format.format(states=''.join(map(str, self)))
        return ''

    @classmethod
    def compile_many(cls: type[_typing.Self], text: str) -> _typing.Iterator[_typing.Self]:
        match: _re.Match[str]
        for match in cls.regex.finditer(text):
            yield cls(FlashcardState.compile_many(text[match.start():match.end()]))

    @classmethod
    def compile(cls: type[_typing.Self], text: str) -> _typing.Self:
        rets: _typing.Iterator[_typing.Self] = cls.compile_many(text)
        try:
            ret: _typing.Self = next(rets)
        except StopIteration as ex:
            raise ValueError(f'No matches: {text}') from ex
        try:
            next(rets)
            raise ValueError(f'Too many matches: {text}')
        except StopIteration:
            pass
        return ret


@_typing.final
class StatefulFlashcardGroup(_typing.NamedTuple):
    flashcard: FlashcardGroup
    state: FlashcardStateGroup

    def __str__(self: _typing.Self) -> str:
        return ' '.join((str(self.flashcard), str(self.state)))
