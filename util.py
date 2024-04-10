# -*- coding: UTF-8 -*-
from . import LOGGER as _LOGGER, OPEN_TEXT_OPTIONS as _OPEN_TXT_OPTS
from abc import ABCMeta as _ABCM
from anyio import Path as _Path
from ast import (
    AST as _AST,
    Expression as _ASTExpr,
    Interactive as _ASTInter,
    Module as _ASTMod,
    unparse as _unparse,
)
from asyncio import gather as _gather, get_running_loop as _run_loop
from asyncstdlib import sync as _sync
from concurrent.futures import Executor as _Executor, ThreadPoolExecutor as _TPExecutor
from contextlib import asynccontextmanager as _actxmgr
from dataclasses import asdict as _asdict, dataclass as _dc
from functools import cache as _cache, partial as _partial, wraps as _wraps
from importlib import import_module as _import
from inspect import isawaitable as _isawait
from itertools import islice as _islice, starmap as _smap
from json import JSONDecodeError as _JSONDecErr, dumps as _dumps, loads as _loads
from marshal import dumps as _m_dumps, loads as _m_loads
from operator import attrgetter as _attrgetter
from os import PathLike as _PathL, remove as _rm
from re import escape as _re_esc
from regex import VERSION0 as _REX_VER0, compile as _rex_comp
from sys import maxunicode as _maxunicode, modules as _mods
from threading import Lock as _TLock
from time import time as _time
from types import CodeType as _Code, ModuleType as _Mod, TracebackType as _Tb
from typing import (
    Any as _Any,
    Awaitable as _Await,
    Callable as _Call,
    Collection as _Collect,
    ClassVar as _ClsVar,
    Generic as _Genic,
    Iterable as _Iter,
    Iterator as _Itor,
    Literal as _Lit,
    Protocol as _Proto,
    Self as _Self,
    Sequence as _Seq,
    TYPE_CHECKING as _TYPE_CHECKING,
    TypeVar as _TVar,
    TypedDict as _TDict,
    cast as _cast,
    final as _fin,
    overload as _overload,
)
from unicodedata import category as _utf_cat
from uuid import uuid4 as _uuid4
from unittest import mock as _mock
from weakref import WeakKeyDictionary as _WkKDict

if _TYPE_CHECKING:
    from _typeshed import ReadableBuffer as _ReadBuf

_T = _TVar("_T")
_T_co = _TVar("_T_co", covariant=True)
_T1_co = _TVar("_T1_co", covariant=True)
_ExtendsUnit = _TVar("_ExtendsUnit", bound="Unit[_Any]")
_ExtendsModuleType = _TVar("_ExtendsModuleType", bound=_Mod)
_PUNCTUATIONS = tuple(
    char for char in map(chr, range(_maxunicode + 1)) if _utf_cat(char).startswith("P")
)
_PUNCTUATION_REGEX = _rex_comp(
    r"(?<={delims})(?<!^(?:{delims})+)(?!$|{delims})".format(
        delims=r"|".join(map(_re_esc, _PUNCTUATIONS))
    ),
    _REX_VER0,
)
_ASYNC_LOCK_THREAD_POOLS = _WkKDict[_TLock, _Call[[], _Executor]]()


@_overload
async def wrap_async(value: _Await[_T]) -> _T: ...


@_overload
async def wrap_async(value: _Await[_T] | _T) -> _T: ...


async def wrap_async(value: _Await[_T] | _T):
    if _isawait(value):
        return await value
    return value


def identity(var: _T) -> _T:
    return var


def constant(var: _T) -> _Call[..., _T]:
    def func(*_: _Any) -> _T:
        return var

    return func


def ignore_args(func: _Call[[], _T]) -> _Call[..., _T]:
    @_wraps(func)
    def func0(*_: _Any) -> _T:
        return func()

    return func0


def tuple1(var: _T) -> tuple[_T]:
    return (var,)


@_actxmgr
async def async_lock(lock: _TLock):
    await _run_loop().run_in_executor(
        _ASYNC_LOCK_THREAD_POOLS.setdefault(lock, _cache(_partial(_TPExecutor, 1)))(),
        lock.acquire,
    )
    try:
        yield lock
    finally:
        lock.release()


def deep_foreach_module(module: _Mod):
    names = set[str]()

    def impl(mod: _Mod) -> _Itor[_Mod]:
        name = mod.__name__
        if name in names:
            return
        names.add(name)
        yield mod
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, _Mod) and attr.__name__.startswith(name):
                yield from impl(attr)

    return impl(module)


def copy_module(module: _ExtendsModuleType) -> _ExtendsModuleType:
    names = discover_module_names(module)
    with _mock.patch.dict(
        _mods,
        {key: val for key, val in _mods.items() if key not in names},
        clear=True,
    ):
        return _import(module.__name__)


def discover_module_names(module: _Mod) -> _Seq[str]:
    return tuple(map(_attrgetter("__name__"), deep_foreach_module(module)))


def abc_subclasshook_check(
    impl_cls: _ABCM,
    cls: _ABCM,
    subclass: type,
    /,
    *,
    names: _Collect[str],
    typing: _Lit["nominal", "structural"] = "nominal",
):
    if cls is impl_cls:
        if typing == "nominal":
            if any(
                c.__subclasshook__(subclass) is False
                for c in cls.__mro__
                if c is not cls and hasattr(c, "__subclasshook__")
            ) or any(
                all(c.__dict__[p] is None for c in subclass.__mro__ if p in c.__dict__)
                for p in names
            ):
                return False
        elif typing == "structural":
            if all(
                c.__subclasshook__(subclass) is not False
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


@_fin
class Unit(_Genic[_T_co]):
    __slots__: _ClsVar = ("__value",)

    def __init__(self, value: _T_co):
        self.__value: _T_co = value

    def counit(self):
        return self.__value

    def bind(self, func: _Call[[_T_co], _ExtendsUnit]):
        return func(self.counit())

    def extend(self, func: _Call[[_Self], _T1_co]) -> "Unit[_T1_co]":
        return Unit(func(self))

    def map(self, func: _Call[[_T_co], _T1_co]) -> "Unit[_T1_co]":
        return Unit(func(self.counit()))

    def join(self: "Unit[_ExtendsUnit]"):
        return self.counit()

    def duplicate(self):
        return Unit(self)


class TypedTuple(_Genic[_T], tuple[_T, ...]):
    __slots__: _ClsVar = ()
    element_type: _ClsVar

    def __init_subclass__(cls, element_type: type[_T], **kwargs: _Any):
        super().__init_subclass__(**kwargs)
        cls.element_type = element_type

    @_overload
    def __new__(cls, iterable: _Iter[_T], /) -> _Self: ...

    @_overload
    def __new__(cls, *items: _T) -> _Self: ...

    def __new__(cls, *items: _Iter[_T] | _T):
        if len(items) == 1 and not isinstance(items[0], cls.element_type):
            return super().__new__(cls, _cast(_Iter[_T], items[0]))
        return super().__new__(cls, _cast(_Iter[_T], items))

    def __repr__(self):
        return type(self).__qualname__ + super().__repr__()


@_fin
class IteratorSequence(_Genic[_T_co], _Seq[_T_co]):
    __slots__: _ClsVar = ("__cache", "__done", "__iterator", "__lock")

    def __init__(self, iterator: _Itor[_T_co]):
        self.__lock = _TLock()
        self.__iterator = iterator
        self.__cache = list[_T_co]()
        self.__done = False

    def __cache_to(self, length: int | None):
        cur_len = len(self.__cache)
        if self.__done or (length is not None and cur_len >= length):
            return cur_len
        if length is None:
            with self.__lock:
                self.__cache.extend(self.__iterator)
            self.__done = True
            return len(self.__cache)
        with self.__lock:
            extend = length - len(self.__cache)
            if extend > 0:
                self.__cache.extend(_islice(self.__iterator, extend))
        new_len = len(self.__cache)
        if new_len < cur_len + extend:
            self.__done = True
        return new_len

    @_overload
    def __getitem__(self, index: int) -> _T_co: ...

    @_overload
    def __getitem__(self, index: slice) -> _Self: ...

    def __getitem__(self, index: int | slice):
        if isinstance(index, int):
            available = self.__cache_to(index + 1)
            if index >= available:
                raise IndexError(index)
            return self.__cache[index]
        return type(self)(_islice(self, index.start, index.stop, index.step))

    def __len__(self):
        return self.__cache_to(None)


assert issubclass(IteratorSequence, _Seq)


@_fin
class Compiler(_Proto):
    def __call__(
        self,
        source: """str
        | _ReadBuf
        | _ASTMod
        | _ASTExpr
        | _ASTInter""",
        filename: "str | _ReadBuf | _PathL[_Any]",
        mode: str,
        flags: int,
        dont_inherit: bool = ...,
        optimize: int = ...,
    ) -> _Code: ...


@_fin
class CompileCache:
    __slots__: _ClsVar = ("__cache", "__cache_names", "__folder")
    __METADATA_FILENAME: _ClsVar = "metadata.json"
    __CACHE_NAME_FORMAT: _ClsVar = "{}.pyc"
    __TIMEOUT: _ClsVar = 86400

    @_fin
    class MetadataKey(_TDict):
        source: str
        filename: str
        mode: str
        flags: int
        dont_inherit: bool
        optimize: int

    @_fin
    class MetadataValue(_TDict):
        cache_name: str
        access_time: int

    @_fin
    class MetadataEntry(_TDict):
        key: "CompileCache.MetadataKey"
        value: "CompileCache.MetadataValue"

    @_fin
    @_dc(
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
        def from_metadata(cls, data: "CompileCache.MetadataKey"):
            return cls(**data)

        def to_metadata(self):
            return CompileCache.MetadataKey(**_asdict(self))

    @_fin
    @_dc(
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
        value: "CompileCache.MetadataValue"
        code: _Code

    @classmethod
    def __time(cls):
        return int(_time())

    def __gen_cache_name(self):
        ret: str = self.__CACHE_NAME_FORMAT.format(str(_uuid4()))
        while ret in self.__cache_names:
            ret = self.__CACHE_NAME_FORMAT.format(str(_uuid4()))
        return ret

    def __init__(self, *, folder: _Path | None):
        self.__folder = folder
        self.__cache = dict[CompileCache.CacheKey, CompileCache.CacheEntry]()
        self.__cache_names = set[str]()

    async def __aenter__(self):
        folder = self.__folder
        if folder is None:
            return self
        await folder.mkdir(parents=True, exist_ok=True)

        async def read_metadata() -> _Collect[CompileCache.MetadataEntry]:
            metadata_path = folder / self.__METADATA_FILENAME
            if not await metadata_path.exists():
                await metadata_path.write_text("[]", **_OPEN_TXT_OPTS)
            async with await metadata_path.open(
                mode="rt", **_OPEN_TXT_OPTS
            ) as metadata_file:
                try:
                    return _loads(await metadata_file.read())
                except _JSONDecErr:
                    return []

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
                file = await path.open(mode="rb")
            except OSError | ValueError:
                _LOGGER.exception(f"Cannot open code cache: {path}")
                return
            try:
                try:
                    code: _Code | None = _m_loads(await file.read())
                    if code is None:
                        raise ValueError
                except EOFError | ValueError | TypeError:
                    _LOGGER.exception(f"Cannot load code cache: {path}")
                    return
            finally:
                await file.aclose()
            self.__cache_names.add(cache_name)
            self.__cache[CompileCache.CacheKey.from_metadata(key)] = (
                CompileCache.CacheEntry(value=value, code=code)
            )

        await _gather(*map(read_entry, await metadata))
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _Tb | None,
    ):
        folder = self.__folder
        if folder is None:
            return
        cur_time = self.__time()

        async def save_cache(
            key: CompileCache.CacheKey,
            cache: CompileCache.CacheEntry,
        ):
            cache_path = folder / cache.value["cache_name"]
            if cur_time - cache.value["access_time"] >= self.__TIMEOUT:
                try:
                    await _sync(_rm)(cache_path)
                except FileNotFoundError:
                    pass
                return
            ret = CompileCache.MetadataEntry(key=key.to_metadata(), value=cache.value)
            if await cache_path.exists():
                return ret
            async with await cache_path.open(mode="wb") as cache_file:
                try:
                    await cache_file.write(_m_dumps(cache.code))
                except ValueError:
                    _LOGGER.exception(f"Cannot save cache with key: {key}")
                    await cache_file.aclose()
                    try:
                        await _sync(_rm)(cache_path)
                    except FileNotFoundError:
                        pass
                    return
            return ret

        async with await (folder / self.__METADATA_FILENAME).open(
            mode="wt", **_OPEN_TXT_OPTS
        ) as metadata_file:
            await metadata_file.write(
                _dumps(
                    tuple(
                        filter(
                            lambda x: x is not None,
                            await _gather(*_smap(save_cache, self.__cache.items())),
                        )
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
            )

    def compile(
        self,
        source: """str
        | _ReadBuf
        | _ASTMod
        | _ASTExpr
        | _ASTInter""",
        filename: "str | _ReadBuf | _PathL[_Any]",
        mode: str,
        flags: int = 0,
        dont_inherit: bool = False,
        optimize: int = -1,
    ):
        compile0 = _partial(
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
        key = CompileCache.CacheKey(
            source=_unparse(source) if isinstance(source, _AST) else repr(source),
            filename=repr(filename),
            mode=mode,
            flags=flags,
            dont_inherit=dont_inherit,
            optimize=optimize,
        )
        try:
            entry = self.__cache[key]
            entry.value["access_time"] = self.__time()
        except KeyError:
            cache_name = self.__gen_cache_name()
            self.__cache_names.add(cache_name)
            self.__cache[key] = entry = CompileCache.CacheEntry(
                value=CompileCache.MetadataValue(
                    cache_name=cache_name, access_time=self.__time()
                ),
                code=compile0(),
            )
        return entry.code

    def __repr__(self):
        return f"{type(self).__qualname__}(folder={self.__folder!r})"


def affix_lines(text: str, /, *, prefix: str = "", suffix: str = ""):
    def ret_gen():
        newline: str = ""
        for line in text.splitlines():
            yield newline
            yield prefix
            yield line
            yield suffix
            newline = "\n"

    return "".join(ret_gen())


def strip_lines(text: str, /, *, chars: str | None = None):
    return "\n".join(line.strip(chars) for line in text.splitlines())


def split_by_punctuations(text: str):
    return _PUNCTUATION_REGEX.splititer(text)
