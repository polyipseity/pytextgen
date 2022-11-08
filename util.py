from __future__ import annotations

import abc as _abc
import ast as _ast
import dataclasses as _dataclasses
import functools as _functools
import itertools as _itertools
import json as _json
import logging as _logging
import marshal as _marshal
import os as _os
import pathlib as _pathlib
import threading as _threading
import time as _time
import types as _types
import typing as _typing
import uuid as _uuid
if _typing.TYPE_CHECKING:
    import _typeshed as _typeshed

from . import globals as _globals

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


def ignore_args(func: _typing.Callable[[], _T]) -> _typing.Callable[..., _T]:
    @_functools.wraps(func)
    def func0(*_: _typing.Any) -> _T:
        return func()
    return func0


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


@_typing.final
class LazyIterableSequence(_typing.Generic[_T_co], _typing.Sequence[_T_co]):
    __slots__: _typing.ClassVar = (
        '__cache', '__done', '__iterable', '__lock',)

    def __init__(self: _typing.Self, iterable: _typing.Iterable[_T_co]) -> None:
        self.__lock: _threading.Lock = _threading.Lock()
        self.__iterable: _typing.Iterable[_T_co] = iterable
        self.__cache: _typing.MutableSequence[_T_co] = []
        self.__done: bool = False

    def __cache_to(self: _typing.Self, length: int | None) -> int:
        cur_len: int = len(self.__cache)
        if self.__done or (length is not None and cur_len >= length):
            return cur_len
        if length is None:
            with self.__lock:
                self.__cache.extend(self.__iterable)
            self.__done = True
            return len(self.__cache)
        with self.__lock:
            extend: int = length - len(self.__cache)
            if extend > 0:
                self.__cache.extend(
                    _itertools.islice(self.__iterable, extend))
        new_len: int = len(self.__cache)
        if new_len < cur_len + extend:
            self.__done = True
        return new_len

    def __getitem__(self: _typing.Self, index: int) -> _T_co:
        available: int = self.__cache_to(index + 1)
        if index >= available:
            raise IndexError(index)
        return self.__cache[index]

    def __len__(self: _typing.Self) -> int:
        return self.__cache_to(None)


assert issubclass(LazyIterableSequence, _typing.Sequence)


@_typing.final
class Compiler(_typing.Protocol):
    def __call__(self: _typing.Self,
                 source: str | _typeshed.ReadableBuffer | _ast.AST,
                 filename: str | _typeshed.ReadableBuffer | _os.PathLike[_typing.Any],
                 mode: str,
                 flags: int = ...,
                 dont_inherit: bool = ...,
                 optimize: int = ...,
                 ) -> _types.CodeType: ...


@_typing.final
class CompileCache:
    __slots__: _typing.ClassVar = ('__cache', '__cache_names', '__folder',)
    __metadata_filename: str = 'metadata.json'
    __cache_name_format: str = '{}.pyc'
    __timeout: int = 86400

    @_typing.final
    class MetadataKey(_typing.TypedDict):
        source: str
        filename: str
        mode: str
        flags: int
        dont_inherit: bool
        optimize: int

    @_typing.final
    class MetadataValue(_typing.TypedDict):
        cache_name: str
        access_time: int

    @_typing.final
    class MetadataEntry(_typing.TypedDict):
        key: CompileCache.MetadataKey
        value: CompileCache.MetadataValue

    @_typing.final
    @_dataclasses.dataclass(init=True,
                            repr=True,
                            eq=True,
                            order=False,
                            unsafe_hash=False,
                            frozen=True,
                            match_args=True,
                            kw_only=True,
                            slots=True,)
    class CacheKey:
        source: str
        filename: str
        mode: str
        flags: int
        dont_inherit: bool
        optimize: int

        @classmethod
        def from_metadata(cls: type[_typing.Self], data: CompileCache.MetadataKey) -> _typing.Self:
            return cls(**data)

        def to_metadata(self: _typing.Self) -> CompileCache.MetadataKey:
            return CompileCache.MetadataKey(**_dataclasses.asdict(self))

    @_typing.final
    @_dataclasses.dataclass(init=True,
                            repr=True,
                            eq=True,
                            order=False,
                            unsafe_hash=False,
                            frozen=True,
                            match_args=True,
                            kw_only=True,
                            slots=True,)
    class CacheEntry:
        value: CompileCache.MetadataValue
        code: _types.CodeType

    @classmethod
    def __time(cls: type[_typing.Self]) -> int:
        return int(_time.time())

    def __gen_cache_name(self: _typing.Self) -> str:
        ret: str = self.__cache_name_format.format(str(_uuid.uuid4()))
        while ret in self.__cache_names:
            ret = self.__cache_name_format.format(str(_uuid.uuid4()))
        return ret

    def __init__(self: _typing.Self, *, folder: _pathlib.Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        self.__folder: _pathlib.Path = folder.resolve(strict=True)
        metadata_path: _pathlib.Path = self.__folder / self.__metadata_filename
        if not metadata_path.exists():
            metadata_path.write_text('[]', **_globals.open_options)
        metadata_file: _typing.TextIO
        with open(metadata_path, mode='rt', **_globals.open_options) as metadata_file:
            metadata: _typing.Collection[CompileCache.MetadataEntry] = _json.load(
                metadata_file)
        self.__cache: _typing.MutableMapping[CompileCache.CacheKey, CompileCache.CacheEntry] = {
        }
        self.__cache_names: _typing.MutableSet[str] = set()
        entry: CompileCache.MetadataEntry
        for entry in metadata:
            try:
                key: CompileCache.MetadataKey = entry['key']
                value: CompileCache.MetadataValue = entry['value']
                cache_name: str = value['cache_name']
            except KeyError:
                continue
            cache_path: _pathlib.Path = self.__folder / cache_name
            try:
                cache_file: _typing.BinaryIO = open(cache_path, mode='rb')
            except OSError | ValueError:
                _logging.exception(
                    f'Cannot open code cache: {cache_path}')
                continue
            with cache_file:
                try:
                    code: _types.CodeType | None = _marshal.load(
                        cache_file)
                    if code is None:
                        raise ValueError
                except EOFError | ValueError | TypeError:
                    _logging.exception(f'Cannot load code cache: {cache_path}')
                    continue
            self.__cache_names.add(cache_name)
            self.__cache[CompileCache.CacheKey.from_metadata(key)] = CompileCache.CacheEntry(
                value=value, code=code)

    def compile(self: _typing.Self,
                source: str | _typeshed.ReadableBuffer | _ast.AST,
                filename: str | _typeshed.ReadableBuffer | _os.PathLike[_typing.Any],
                mode: str,
                flags: int = 0,
                dont_inherit: bool = False,
                optimize: int = -1,
                ) -> _types.CodeType:
        key: CompileCache.CacheKey = CompileCache.CacheKey(
            source=repr(source), filename=repr(filename), mode=mode, flags=flags, dont_inherit=dont_inherit, optimize=optimize)
        try:
            entry: CompileCache.CacheEntry = self.__cache[key]
            entry.value['access_time'] = self.__time()
        except KeyError:
            cache_name: str = self.__gen_cache_name()
            self.__cache_names.add(cache_name)
            self.__cache[key] = entry = CompileCache.CacheEntry(
                value=CompileCache.MetadataValue(
                    cache_name=cache_name, access_time=self.__time()),
                code=compile(source=source, filename=filename, mode=mode,
                             flags=flags, dont_inherit=dont_inherit, optimize=optimize),
            )
        return entry.code

    def save(self: _typing.Self) -> None:
        cur_time: int = self.__time()

        def save_cache() -> _typing.Iterator[CompileCache.MetadataEntry]:
            key: CompileCache.CacheKey
            cache: CompileCache.CacheEntry
            for key, cache in self.__cache.items():
                cache_path: _pathlib.Path = (
                    self.__folder / cache.value['cache_name'])
                if cur_time - cache.value['access_time'] >= self.__timeout:
                    try:
                        _os.remove(cache_path)
                    except FileNotFoundError:
                        pass
                    continue
                if cache_path.exists():
                    continue
                cache_file: _typing.BinaryIO
                with open(cache_path, mode='wb') as cache_file:
                    try:
                        _marshal.dump(cache.code, cache_file)
                    except ValueError:
                        _logging.exception(
                            f'Cannot save cache with key: {key}')
                        cache_file.close()
                        try:
                            _os.remove(cache_path)
                        except FileNotFoundError:
                            pass
                        continue
                yield CompileCache.MetadataEntry(key=key.to_metadata(), value=cache.value)

        metadata_file: _typing.TextIO
        with open(self.__folder / self.__metadata_filename, mode='wt', **_globals.open_options) as metadata_file:
            _json.dump(tuple(save_cache()), metadata_file,
                       ensure_ascii=False, sort_keys=True, indent=2)

    def __repr__(self: _typing.Self) -> str:
        return f'{type(self).__qualname__}(folder={self.__folder!r})'
