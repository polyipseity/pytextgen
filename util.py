# -*- coding: UTF-8 -*-
from __future__ import annotations
import abc as _abc
import aiofiles as _aiofiles
import ast as _ast
import asyncio as _asyncio
import dataclasses as _dataclasses
import functools as _functools
import importlib as _importlib
import itertools as _itertools
import json as _json
import logging as _logging
import marshal as _marshal
import os as _os
import pathlib as _pathlib
import sys as _sys
import threading as _threading
import time as _time
import types as _types
import typing as _typing
import uuid as _uuid
import unittest.mock as _unittest_mock

from . import globals as _globals

if _typing.TYPE_CHECKING:
    import _typeshed as _typeshed

_T = _typing.TypeVar("_T")
_T_co = _typing.TypeVar("_T_co", covariant=True)
_T1_co = _typing.TypeVar("_T1_co", covariant=True)
_ExtendsUnit = _typing.TypeVar("_ExtendsUnit", bound="Unit[_typing.Any]")
_ExtendsModuleType = _typing.TypeVar("_ExtendsModuleType", bound=_types.ModuleType)
StrPath = str | _os.PathLike[str]


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


async def maybe_async(value: _typing.Awaitable[_T] | _T) -> _T:
    if isinstance(value, _typing.Awaitable):
        value0: _typing.Awaitable[_T] = value
        return await value0
    return value


def copy_module(module: _ExtendsModuleType) -> _ExtendsModuleType:
    names = set[str]()

    def discover_names(mod: _types.ModuleType):
        name = mod.__name__
        if name in names:
            return
        names.add(name)
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, _types.ModuleType) and attr.__name__.startswith(name):
                discover_names(attr)

    discover_names(module)
    with _unittest_mock.patch.dict(
        _sys.modules,
        {key: val for key, val in _sys.modules.items() if key not in names},
        clear=True,
    ):
        return _importlib.import_module(module.__name__)


def abc_subclasshook_check(
    impl_cls: _abc.ABCMeta,
    cls: _abc.ABCMeta,
    subclass: type,
    /,
    *,
    names: _typing.Collection[str],
    typing: _typing.Literal["nominal", "structural"] = "nominal",
) -> bool | _types.NotImplementedType:
    if cls is impl_cls:
        if typing == "nominal":
            if any(
                getattr(c, "__subclasshook__")(subclass) is False
                for c in cls.__mro__
                if c is not cls and hasattr(c, "__subclasshook__")
            ) or any(
                all(c.__dict__[p] is None for c in subclass.__mro__ if p in c.__dict__)
                for p in names
            ):
                return False
        elif typing == "structural":
            if all(
                getattr(c, "__subclasshook__")(subclass) is not False
                for c in cls.__mro__
                if c is not cls and hasattr(c, "__subclasshook__")
            ) and all(
                any(
                    c.__dict__[p] is not None
                    for c in subclass.__mro__
                    if p in c.__dict__
                )
                for p in names
            ):
                return True
        else:
            raise ValueError(typing)
    return NotImplemented


@_typing.final
class Unit(_typing.Generic[_T_co]):
    __slots__: _typing.ClassVar = ("__value",)

    def __init__(self, value: _T_co) -> None:
        self.__value: _T_co = value

    def counit(self) -> _T_co:
        return self.__value

    def bind(self, func: _typing.Callable[[_T_co], _ExtendsUnit]) -> _ExtendsUnit:
        return func(self.counit())

    def extend(self, func: _typing.Callable[[_typing.Self], _T1_co]) -> "Unit[_T1_co]":
        return Unit(func(self))

    def map(self, func: _typing.Callable[[_T_co], _T1_co]) -> "Unit[_T1_co]":
        return Unit(func(self.counit()))

    def join(self: "Unit[_ExtendsUnit]") -> _ExtendsUnit:
        return self.counit()

    def duplicate(self) -> "Unit[_typing.Self]":
        return Unit(self)


class TypedTuple(_typing.Generic[_T], tuple[_T, ...]):
    __slots__: _typing.ClassVar = ()
    element_type: type[_T]

    def __init_subclass__(cls, element_type: type[_T], **kwargs: _typing.Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.element_type = element_type

    @_typing.overload
    def __new__(cls, iterable: _typing.Iterable[_T], /) -> _typing.Self:
        ...

    @_typing.overload
    def __new__(cls, *items: _T) -> _typing.Self:
        ...

    def __new__(cls, *items: _typing.Iterable[_T] | _T) -> _typing.Self:
        if len(items) == 1 and not isinstance(items[0], cls.element_type):
            return super().__new__(cls, _typing.cast(_typing.Iterable[_T], items[0]))
        return super().__new__(cls, _typing.cast(_typing.Iterable[_T], items))

    def __repr__(self) -> str:
        return type(self).__qualname__ + super().__repr__()


@_typing.final
class LazyIterableSequence(_typing.Generic[_T_co], _typing.Sequence[_T_co]):
    __slots__: _typing.ClassVar = ("__cache", "__done", "__iterable", "__lock")

    def __init__(self, iterable: _typing.Iterable[_T_co]) -> None:
        self.__lock: _threading.Lock = _threading.Lock()
        self.__iterable: _typing.Iterable[_T_co] = iterable
        self.__cache: _typing.MutableSequence[_T_co] = []
        self.__done: bool = False

    def __cache_to(self, length: int | None) -> int:
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
                self.__cache.extend(_itertools.islice(self.__iterable, extend))
        new_len: int = len(self.__cache)
        if new_len < cur_len + extend:
            self.__done = True
        return new_len

    def __getitem__(self, index: int) -> _T_co:
        available: int = self.__cache_to(index + 1)
        if index >= available:
            raise IndexError(index)
        return self.__cache[index]

    def __len__(self) -> int:
        return self.__cache_to(None)


assert issubclass(LazyIterableSequence, _typing.Sequence)


@_typing.final
class Compiler(_typing.Protocol):
    def __call__(
        self,
        source: str
        | _typeshed.ReadableBuffer
        | _ast.Module
        | _ast.Expression
        | _ast.Interactive,
        filename: str | _typeshed.ReadableBuffer | _os.PathLike[_typing.Any],
        mode: str,
        flags: int,
        dont_inherit: bool = ...,
        optimize: int = ...,
    ) -> _types.CodeType:
        ...


@_typing.final
class CompileCache:
    __slots__: _typing.ClassVar = ("__cache", "__cache_names", "__folder")
    __METADATA_FILENAME: _typing.ClassVar = "metadata.json"
    __CACHE_NAME_FORMAT: _typing.ClassVar = "{}.pyc"
    __TIMEOUT: _typing.ClassVar = 86400

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
    class CacheKey:
        source: str
        filename: str
        mode: str
        flags: int
        dont_inherit: bool
        optimize: int

        @classmethod
        def from_metadata(cls, data: CompileCache.MetadataKey) -> _typing.Self:
            return cls(**data)

        def to_metadata(self) -> CompileCache.MetadataKey:
            return CompileCache.MetadataKey(**_dataclasses.asdict(self))

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
    class CacheEntry:
        value: CompileCache.MetadataValue
        code: _types.CodeType

    @classmethod
    def __time(cls) -> int:
        return int(_time.time())

    def __gen_cache_name(self) -> str:
        ret: str = self.__CACHE_NAME_FORMAT.format(str(_uuid.uuid4()))
        while ret in self.__cache_names:
            ret = self.__CACHE_NAME_FORMAT.format(str(_uuid.uuid4()))
        return ret

    def __init__(self, *, folder: _pathlib.Path | None):
        if folder is None:
            self.__folder = None
        else:
            folder.mkdir(parents=True, exist_ok=True)
            self.__folder = folder.resolve(strict=True)
        self.__cache: _typing.MutableMapping[
            CompileCache.CacheKey, CompileCache.CacheEntry
        ] = {}
        self.__cache_names: _typing.MutableSet[str] = set()

    async def __aenter__(self):
        folder = self.__folder
        if folder is None:
            return self

        async def read_metadata():
            metadata_path: _pathlib.Path = folder / self.__METADATA_FILENAME
            if not metadata_path.exists():
                metadata_path.write_text("[]", **_globals.OPEN_OPTIONS)
            async with _aiofiles.open(
                metadata_path, mode="rt", **_globals.OPEN_OPTIONS
            ) as metadata_file:
                metadata: _typing.Collection[CompileCache.MetadataEntry] = _json.loads(
                    await metadata_file.read()
                )
                return metadata

        metadata = read_metadata()

        async def read_entry(entry: CompileCache.MetadataEntry):
            try:
                key: CompileCache.MetadataKey = entry["key"]
                value: CompileCache.MetadataValue = entry["value"]
                cache_name: str = value["cache_name"]
            except KeyError:
                return
            path = folder / cache_name
            try:
                file = await _aiofiles.open(path, mode="rb")
            except OSError | ValueError:
                _logging.exception(f"Cannot open code cache: {path}")
                return
            try:
                try:
                    code: _types.CodeType | None = _marshal.loads(await file.read())
                    if code is None:
                        raise ValueError
                except EOFError | ValueError | TypeError:
                    _logging.exception(f"Cannot load code cache: {path}")
                    return
            finally:
                await file.close()
            self.__cache_names.add(cache_name)
            self.__cache[
                CompileCache.CacheKey.from_metadata(key)
            ] = CompileCache.CacheEntry(value=value, code=code)

        await _asyncio.gather(*map(read_entry, await metadata))
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _types.TracebackType | None,
    ):
        folder = self.__folder
        if folder is None:
            return
        cur_time: int = self.__time()

        async def save_cache(
            key: CompileCache.CacheKey,
            cache: CompileCache.CacheEntry,
        ):
            cache_path: _pathlib.Path = folder / cache.value["cache_name"]
            if cur_time - cache.value["access_time"] >= self.__TIMEOUT:
                try:
                    _os.remove(cache_path)
                except FileNotFoundError:
                    pass
                return
            if cache_path.exists():
                return
            async with _aiofiles.open(cache_path, mode="wb") as cache_file:
                try:
                    await cache_file.write(_marshal.dumps(cache.code))
                except ValueError:
                    _logging.exception(f"Cannot save cache with key: {key}")
                    await cache_file.close()
                    try:
                        _os.remove(cache_path)
                    except FileNotFoundError:
                        pass
                    return
            return CompileCache.MetadataEntry(key=key.to_metadata(), value=cache.value)

        async with _aiofiles.open(
            folder / self.__METADATA_FILENAME, mode="wt", **_globals.OPEN_OPTIONS
        ) as metadata_file:
            await metadata_file.write(
                _json.dumps(
                    tuple(
                        filter(
                            lambda x: x is not None,
                            await _asyncio.gather(
                                *_itertools.starmap(
                                    save_cache,
                                    self.__cache.items(),
                                )
                            ),
                        )
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
            )

    def compile(
        self,
        source: str
        | _typeshed.ReadableBuffer
        | _ast.Module
        | _ast.Expression
        | _ast.Interactive,
        filename: str | _typeshed.ReadableBuffer | _os.PathLike[_typing.Any],
        mode: str,
        flags: int = 0,
        dont_inherit: bool = False,
        optimize: int = -1,
    ) -> _types.CodeType:
        compile0 = _functools.partial(
            compile,
            source=source,
            filename=filename,
            mode=mode,
            flags=flags,
            dont_inherit=dont_inherit,
            optimize=optimize,
        )
        folder = self.__folder
        if folder is None:
            return compile0()
        key: CompileCache.CacheKey = CompileCache.CacheKey(
            source=_ast.unparse(source)
            if isinstance(source, _ast.AST)
            else repr(source),
            filename=repr(filename),
            mode=mode,
            flags=flags,
            dont_inherit=dont_inherit,
            optimize=optimize,
        )
        try:
            entry: CompileCache.CacheEntry = self.__cache[key]
            entry.value["access_time"] = self.__time()
        except KeyError:
            cache_name: str = self.__gen_cache_name()
            self.__cache_names.add(cache_name)
            self.__cache[key] = entry = CompileCache.CacheEntry(
                value=CompileCache.MetadataValue(
                    cache_name=cache_name, access_time=self.__time()
                ),
                code=compile0(),
            )
        return entry.code

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(folder={self.__folder!r})"
