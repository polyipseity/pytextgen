"""Small, well-tested utility helpers used by the package.

This module provides small composable helpers (sync/async wrappers),
protocols, and a small compile cache used by the `generate` path.
"""

import json
import marshal
from abc import ABCMeta
from ast import AST, Expression, Interactive, Module, unparse
from asyncio import gather, get_running_loop
from concurrent.futures import Executor, ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict, dataclass
from functools import cache, partial, wraps
from importlib import import_module
from importlib.util import MAGIC_NUMBER
from inspect import isawaitable
from itertools import islice, starmap
from json import JSONDecodeError
from operator import attrgetter
from os import PathLike, remove
from re import escape
from sys import maxunicode, modules
from threading import Lock
from time import time
from types import CodeType, ModuleType, TracebackType
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    ClassVar,
    Collection,
    Generic,
    Iterable,
    Iterator,
    Literal,
    Protocol,
    Self,
    Sequence,
    TypedDict,
    TypeVar,
    cast,
    final,
    overload,
)
from unicodedata import category
from unittest import mock
from uuid import uuid4
from weakref import WeakKeyDictionary

import regex
from aioshutil import sync_to_async
from anyio import Path

from .meta import LOGGER, OPEN_TEXT_OPTIONS

__all__ = (
    "wrap_async",
    "identity",
    "constant",
    "ignore_args",
    "tuple1",
    "async_lock",
    "deep_foreach_module",
    "copy_module",
    "discover_module_names",
    "abc_subclasshook_check",
    "Unit",
    "TypedTuple",
    "IteratorSequence",
    "Compiler",
    "CompileCache",
    "affix_lines",
    "strip_lines",
    "split_by_punctuations",
)

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_T1_co = TypeVar("_T1_co", covariant=True)
_ExtendsUnit = TypeVar("_ExtendsUnit", bound="Unit[Any]")
_PUNCTUATIONS = tuple(
    char for char in map(chr, range(maxunicode + 1)) if category(char).startswith("P")
)
_PUNCTUATION_REGEX = regex.compile(
    r"(?<={delims})(?<!^(?:{delims})+)(?!$|{delims})".format(
        delims=r"|".join(map(escape, _PUNCTUATIONS))
    ),
    regex.VERSION0,
)
_ASYNC_LOCK_THREAD_POOLS: WeakKeyDictionary[Lock, Callable[[], Executor]] = (
    WeakKeyDictionary()
)
rm_a = sync_to_async(remove)


@overload
async def wrap_async(value: Awaitable[_T]) -> _T:
    """Await and return the underlying value when awaitable (overload)."""
    ...


@overload
async def wrap_async(value: Awaitable[_T] | _T) -> _T:
    """Await and return the underlying value when awaitable (overload)."""
    ...


async def wrap_async(value: Awaitable[_T] | _T):
    """Await and return the underlying value when awaitable.

    This helper ensures that both plain values and awaitable values may
    be handled transparently in async contexts.
    """
    if isawaitable(value):
        return await value
    return value


def identity(var: _T) -> _T:
    """Return the given value unchanged (identity function)."""
    return var


def constant(var: _T) -> Callable[..., _T]:
    """Return a callable that always returns `var`.

    Useful for providing default callbacks or constant factories.
    """

    def func(*_: Any) -> _T:
        return var

    return func


def ignore_args(func: Callable[[], _T]) -> Callable[..., _T]:
    """Wrap a no-argument callable so it can accept and ignore extra args.

    The returned function forwards no positional or keyword arguments to
    the underlying `func` and returns its result.
    """

    @wraps(func)
    def func0(*_: Any) -> _T:
        return func()

    return func0


def tuple1(var: _T) -> tuple[_T]:
    """Return a 1-tuple containing `var`.

    This helper improves readability at call-sites that expect a tuple.
    """
    return (var,)


@asynccontextmanager
async def async_lock(lock: Lock) -> AsyncIterator[Lock]:
    """Async context manager to acquire and release a threading lock.

    This runs the blocking `lock.acquire` in a threadpool so it may be
    used from async code.
    """
    await get_running_loop().run_in_executor(
        _ASYNC_LOCK_THREAD_POOLS.setdefault(
            lock, cache(partial(ThreadPoolExecutor, 1))
        )(),
        lock.acquire,
    )
    try:
        yield lock
    finally:
        lock.release()


def deep_foreach_module(module: ModuleType):
    """Yield modules from a package and its submodules, recursively.

    Prevents revisiting modules by keeping track of seen module names.
    """
    names = set[str]()

    def impl(mod: ModuleType) -> Iterator[ModuleType]:
        name = mod.__name__
        if name in names:
            return
        names.add(name)
        yield mod
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if isinstance(attr, ModuleType) and attr.__name__.startswith(name):
                yield from impl(attr)

    return impl(module)


def copy_module(module: ModuleType) -> ModuleType:
    """Create a fresh import of `module` with unrelated module cache.

    This temporarily clears unrelated modules from `sys.modules` and
    re-imports the requested module so consumers have a clean copy.
    """
    names = discover_module_names(module)
    with mock.patch.dict(
        modules,
        {key: val for key, val in modules.items() if key not in names},
        clear=True,
    ):
        return import_module(module.__name__)


def discover_module_names(module: ModuleType) -> Sequence[str]:
    """Return a sequence of full module names for `module` and submodules."""
    return tuple(map(attrgetter("__name__"), deep_foreach_module(module)))


def abc_subclasshook_check(
    impl_cls: ABCMeta,
    cls: ABCMeta,
    subclass: type,
    /,
    *,
    names: Collection[str],
    typing: Literal["nominal", "structural"] = "nominal",
):
    """Helper used in `__subclasshook__` implementations.

    Supports both nominal and structural checks for the presence of
    attributes specified by `names`. Returns `True`, `False` or
    `NotImplemented` to be used directly from `__subclasshook__`.
    """
    if cls is impl_cls:
        if typing == "nominal":
            if any(
                c.__subclasshook__(subclass) is False
                for c in cls.__mro__
                if c is not cls  # type: ignore[reportUnnecessaryComparison]
                and hasattr(c, "__subclasshook__")
            ) or any(
                all(c.__dict__[p] is None for c in subclass.__mro__ if p in c.__dict__)
                for p in names
            ):
                return False
        elif typing == "structural":
            if all(
                c.__subclasshook__(subclass) is not False
                for c in cls.__mro__
                if c is not cls  # type: ignore[reportUnnecessaryComparison]
                and hasattr(c, "__subclasshook__")
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


@final
class Unit(Generic[_T_co]):
    """A tiny container type wrapping a single value.

    Provides monadic-style helpers: `counit`, `bind`, `map`, `join` and
    `duplicate` for simple composition in utility code and tests.
    """

    __slots__: ClassVar = ("__value",)

    def __init__(self, value: _T_co):
        """Store the wrapped value inside the `Unit` container."""
        self.__value: _T_co = value

    def counit(self):
        """Return the wrapped value."""
        return self.__value

    def bind(self, func: Callable[[_T_co], _ExtendsUnit]):
        """Apply `func` to the wrapped value and return its result."""
        return func(self.counit())

    def extend(self, func: Callable[[Self], _T1_co]) -> "Unit[_T1_co]":
        """Extend the current `Unit` using `func` producing a new `Unit`."""
        return Unit(func(self))

    def map(self, func: Callable[[_T_co], _T1_co]) -> "Unit[_T1_co]":
        """Map `func` over the contained value and wrap the result."""
        return Unit(func(self.counit()))

    def join(self: "Unit[_ExtendsUnit]"):
        """Flatten one level of `Unit` by returning the inner value."""
        return self.counit()

    def duplicate(self):
        """Return a new `Unit` that wraps this `Unit`."""
        return Unit(self)


class TypedTuple(Generic[_T], tuple[_T, ...]):
    """A typed tuple with a fixed element type provided at subclassing.

    Subclass by providing `element_type` to ensure the tuple contains only
    elements of that type at construction time.
    """

    __slots__: ClassVar = ()
    element_type: type[_T]

    def __init_subclass__(cls, element_type: type[_T], **kwargs: Any):
        """Record the required `element_type` for this `TypedTuple` subclass."""
        super().__init_subclass__(**kwargs)
        cls.element_type = element_type

    @overload
    def __new__(cls, iterable: Iterable[_T], /) -> Self:
        """Overload: construct from iterable."""
        ...

    @overload
    def __new__(cls, *items: _T) -> Self:
        """Overload: construct from explicit items."""
        ...

    def __new__(cls, *items: Iterable[_T] | _T):
        """Construct a `TypedTuple` enforcing `element_type` at creation time."""
        if len(items) == 1 and not isinstance(items[0], cls.element_type):
            return super().__new__(cls, cast(Iterable[_T], items[0]))
        return super().__new__(cls, cast(Iterable[_T], items))

    def __repr__(self):
        """Include the subclass name in the tuple representation."""
        return type(self).__qualname__ + super().__repr__()


@final
class IteratorSequence(Generic[_T_co], Sequence[_T_co]):
    """A sequence view over an iterator that supports len() and indexing.

    Caches yielded values under a lock so the sequence can be iterated and
    randomly accessed safely from multiple callers.
    """

    __slots__: ClassVar = ("__cache", "__done", "__iterator", "__lock")

    def __init__(self, iterator: Iterator[_T_co]):
        """Initialise the sequence view over `iterator`, preparing cache and lock."""
        self.__lock = Lock()
        self.__iterator = iterator
        self.__cache = list[_T_co]()
        self.__done = False

    def __cache_to(self, length: int | None):
        """Ensure the internal cache contains up to `length` items (or all if None)."""
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
                self.__cache.extend(islice(self.__iterator, extend))
        new_len = len(self.__cache)
        if new_len < cur_len + extend:
            self.__done = True
        return new_len

    @overload
    def __getitem__(self, index: int) -> _T_co:
        """Overload: index returns single element."""
        ...

    @overload
    def __getitem__(self, index: slice) -> Self:
        """Overload: slice returns a new sequence view."""
        ...

    def __getitem__(self, index: int | slice):
        """Return cached item(s) by index; populate cache on demand."""
        if isinstance(index, int):
            available = self.__cache_to(index + 1)
            if index >= available:
                raise IndexError(index)
            return self.__cache[index]
        return type(self)(islice(self, index.start, index.stop, index.step))

    def __len__(self):
        """Return the total number of elements, exhausting the iterator if needed."""
        return self.__cache_to(None)


assert issubclass(IteratorSequence, Sequence)


@final
class Compiler(Protocol):
    """Protocol for a callable compatible with the built-in `compile`.

    Represents an object that accepts source and compilation parameters
    and returns a Python code object.
    """

    def __call__(
        self,
        source: "str | ReadableBuffer | Module | Expression | Interactive",
        filename: "str | bytes | PathLike[Any]",
        mode: str,
        flags: int,
        dont_inherit: bool = ...,
        optimize: int = ...,
    ) -> CodeType:
        """Protocol signature: compile-source callable compatible with `compile`.

        Implementations should accept the same parameters as built-in `compile`
        and return a code object.
        """
        ...


@final
class CompileCache:
    """A small on-disk/memory cache for compiled Python code objects.

    Use as an async context manager. When `folder` is provided compiled
    code is stored on disk along with metadata; otherwise caching is
    kept in-memory for the context lifetime.
    """

    __slots__: ClassVar = ("__cache", "__cache_names", "__folder")
    __METADATA_FILENAME: ClassVar = "metadata.json"
    __CACHE_NAME_FORMAT: ClassVar = "{}.pyc"
    __TIMEOUT: ClassVar = 86400

    @final
    class MetadataKey(TypedDict):
        source: str
        filename: str
        magic_number: int
        mode: str
        flags: int
        dont_inherit: bool
        optimize: int

    @final
    class MetadataValue(TypedDict):
        cache_name: str
        access_time: int

    @final
    class MetadataEntry(TypedDict):
        key: "CompileCache.MetadataKey"
        value: "CompileCache.MetadataValue"

    @final
    @dataclass(
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
        magic_number: int
        mode: str
        flags: int
        dont_inherit: bool
        optimize: int

        @classmethod
        def from_metadata(cls, data: "CompileCache.MetadataKey"):
            return cls(**data)

        def to_metadata(self):
            return CompileCache.MetadataKey(**asdict(self))

    @final
    @dataclass(
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
        code: CodeType

    @classmethod
    def __time(cls):
        """Return the current epoch time as an integer (seconds)."""
        return int(time())

    def __gen_cache_name(self):
        """Generate a unique filename for storing compiled cache entries."""
        ret: str = self.__CACHE_NAME_FORMAT.format(str(uuid4()))
        while ret in self.__cache_names:
            ret = self.__CACHE_NAME_FORMAT.format(str(uuid4()))
        return ret

    def __init__(self, *, folder: PathLike[Any] | None):
        """Create a compile cache optionally backed by a filesystem `folder`."""
        self.__folder = None if folder is None else Path(folder)
        self.__cache = dict[CompileCache.CacheKey, CompileCache.CacheEntry]()
        self.__cache_names = set[str]()

    async def __aenter__(self):
        """Async enter: load on-disk metadata and cached compiled code if a folder is set."""
        folder = self.__folder
        if folder is None:
            return self
        await folder.mkdir(parents=True, exist_ok=True)

        async def read_metadata() -> Collection[CompileCache.MetadataEntry]:
            metadata_path = folder / self.__METADATA_FILENAME
            if not await metadata_path.exists():
                await metadata_path.write_text("[]", **OPEN_TEXT_OPTIONS)
            async with await metadata_path.open(
                mode="rt", **OPEN_TEXT_OPTIONS
            ) as metadata_file:
                try:
                    return json.loads(await metadata_file.read())
                except JSONDecodeError:
                    return []

        async def read_entry(entry: CompileCache.MetadataEntry):
            try:
                key: CompileCache.MetadataKey = entry["key"]
                value: CompileCache.MetadataValue = entry["value"]
                cache_name: str = value["cache_name"]
            except KeyError:
                LOGGER.exception(f"Cannot read entry: {entry}")
                return
            path = folder / cache_name
            try:
                key2 = CompileCache.CacheKey.from_metadata(key)
            except TypeError:
                LOGGER.exception(f"Cannot parse key: {key}")
                with suppress(FileNotFoundError, OSError):
                    await rm_a(path)
                return
            try:
                file = await path.open(mode="rb")
            except (OSError, ValueError):
                LOGGER.exception(f"Cannot open code cache: {path}")
                with suppress(FileNotFoundError, OSError):
                    await rm_a(path)
                return
            async with file:
                try:
                    code: CodeType | None = marshal.loads(await file.read())
                    if code is None:
                        raise ValueError
                except (EOFError, ValueError, TypeError):
                    LOGGER.exception(f"Cannot load code cache: {path}")
                    return
            self.__cache_names.add(cache_name)
            self.__cache[key2] = CompileCache.CacheEntry(value=value, code=code)

        await gather(*map(read_entry, await read_metadata()))
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ):
        """Async-exit: persist cache metadata and write any on-disk entries."""
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
                with suppress(FileNotFoundError, OSError):
                    await rm_a(cache_path)
                return
            ret = CompileCache.MetadataEntry(key=key.to_metadata(), value=cache.value)
            if await cache_path.exists():
                return ret
            async with await cache_path.open(mode="wb") as cache_file:
                try:
                    await cache_file.write(marshal.dumps(cache.code))
                except ValueError:
                    LOGGER.exception(f"Cannot save cache with key: {key}")
                    await cache_file.aclose()
                    try:
                        await rm_a(cache_path)
                    except FileNotFoundError:
                        pass
                    return
            return ret

        async with await (folder / self.__METADATA_FILENAME).open(
            mode="wt", **OPEN_TEXT_OPTIONS
        ) as metadata_file:
            await metadata_file.write(
                json.dumps(
                    tuple(
                        filter(
                            lambda x: x is not None,
                            await gather(*starmap(save_cache, self.__cache.items())),
                        )
                    ),
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                )
            )

    def compile(
        self,
        source: "str | ReadableBuffer | Module | Expression | Interactive",
        filename: "str | bytes | PathLike[Any]",
        mode: str,
        flags: int = 0,
        dont_inherit: bool = False,
        optimize: int = -1,
    ):
        """Compile `source` and return a cached code object when available.

        If a folder was provided to the cache the compiled code may be
        persisted and reused across context lifetimes.
        """
        compile0 = partial(
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
            source=unparse(source) if isinstance(source, AST) else repr(source),
            filename=repr(filename),
            magic_number=int.from_bytes(MAGIC_NUMBER),
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
        """Return a concise representation showing the backing folder (if any)."""
        return f"{type(self).__qualname__}(folder={self.__folder!r})"


def affix_lines(text: str, /, *, prefix: str = "", suffix: str = ""):
    """Return `text` with `prefix` and `suffix` inserted around each line.

    Useful for constructing joined lines with consistent pre/post text.
    """

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
    """Strip each line in `text` and return the joined result."""
    return "\n".join(line.strip(chars) for line in text.splitlines())


def split_by_punctuations(text: str):
    """Split `text` into parts using Unicode punctuation boundaries."""
    return _PUNCTUATION_REGEX.splititer(text)
