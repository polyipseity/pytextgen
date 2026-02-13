"""Reader abstractions and the `MarkdownReader` implementation.

Provides a pluggable `Reader` interface and a Markdown reader which
extracts embedded Python code blocks for later execution.
"""

import builtins
import re
from abc import ABCMeta, abstractmethod
from ast import parse
from asyncio import AbstractEventLoop, get_running_loop
from asyncio import Lock as AsyncLock
from collections import defaultdict
from collections.abc import Iterable
from contextlib import (
    AbstractContextManager,
    asynccontextmanager,
    contextmanager,
    nullcontext,
)
from dataclasses import replace
from datetime import date
from functools import cache, partial, wraps
from importlib import import_module
from itertools import chain, repeat
from os.path import splitext
from sys import modules
from threading import Lock as ThreadLock
from types import CodeType, MappingProxyType, ModuleType
from typing import (
    Any,
    AsyncIterator,
    Callable,
    ClassVar,
    Collection,
    Iterator,
    Mapping,
    Self,
    Sequence,
)
from unittest import mock
from weakref import WeakKeyDictionary

from anyio import Path
from asyncstdlib import chain as achain
from asyncstdlib import tuple as atuple
from more_itertools import unique_everseen

from ..meta import FLASHCARD_EASE_DEFAULT, NAME, OPEN_TEXT_OPTIONS
from ..utils import (
    abc_subclasshook_check,
    async_lock,
    copy_module,
    deep_foreach_module,
    ignore_args,
)
from .env import Environment
from .options import GenOpts
from .utils import NULL_LOCATION, FileSection
from .virenv.utils import StatefulFlashcardGroup
from .write import PythonWriter, Writer

__all__ = ("Reader", "CodeLibrary", "MarkdownReader")

_PYTHON_ENV_BUILTINS_EXCLUDE = frozenset[str](
    # constants: https://docs.python.org/library/constants.html
    # functions: https://docs.python.org/library/functions.html
)
_PYTHON_ENV_MODULE_LOCKS: WeakKeyDictionary[
    AbstractEventLoop, Callable[[], AsyncLock]
] = WeakKeyDictionary()
_PYTHON_ENV_MODULE_CACHE: WeakKeyDictionary[
    AbstractEventLoop, tuple[ModuleType, Mapping[str, ModuleType]]
] = WeakKeyDictionary()


class Reader(metaclass=ABCMeta):
    """Abstract reader interface for file-like inputs.

    Subclasses should implement `read` and `pipe`. Use `Reader.register2`
    to register file extensions handled by concrete readers.
    """

    __slots__: ClassVar = ()
    REGISTRY: ClassVar = dict[str, type[Self]]()
    __CACHE: ClassVar = dict[Path, Self]()
    __CACHE_LOCKS: ClassVar = defaultdict[Path, ThreadLock](ThreadLock)

    @classmethod
    def register2(cls, *extensions: str):
        """Decorator factory: register a Reader subclass for additional extensions.

        Mirrors `Reader.register` behaviour while also assigning the class to
        the `REGISTRY` for each supplied file extension.
        """

        @wraps(cls.register)
        def register(subclass: type[Self]) -> type[Self]:
            ret = cls.register(subclass)
            for ext in extensions:
                cls.REGISTRY[ext] = subclass
            return ret

        return register

    @classmethod
    async def new(cls, *, path: Path, options: GenOpts):
        """Create and populate a new reader instance for `path`.

        Reads the file from disk and calls the reader's ``read`` coroutine to
        initialise internal state.
        """
        _, ext = splitext(path)
        ret = cls.REGISTRY[ext](path=path, options=options)
        async with await path.open(mode="rt", **OPEN_TEXT_OPTIONS) as io:
            await ret.read(await io.read())
        return ret

    @classmethod
    async def cached(cls, *, path: Path, options: GenOpts):
        """Return a cached `Reader` for `path`, creating it if necessary.

        Ensures only one reader is created per path using an async lock.
        """
        path = await path.resolve(strict=True)
        async with async_lock(cls.__CACHE_LOCKS[path]):
            try:
                return cls.__CACHE[path]
            except KeyError:
                ret = cls.__CACHE[path] = await cls.new(path=path, options=options)
        return ret

    @abstractmethod
    def __init__(self, *, path: Path, options: GenOpts):
        """Construct a `Reader` for `path` with the given generation `options`.

        Concrete readers must call `super().__init__` (if needed) and set up
        any internal state required for `read`/`pipe` operations.
        """
        raise NotImplementedError(self)

    @property
    @abstractmethod
    def path(self) -> Path:
        """Filesystem `Path` handled by this reader."""
        raise NotImplementedError(self)

    @property
    @abstractmethod
    def options(self) -> GenOpts:
        """Generation options (`GenOpts`) used by this reader."""
        raise NotImplementedError(self)

    @abstractmethod
    async def read(self, text: str, /) -> None:
        """Parse and consume the textual contents of the underlying file.

        Implementations should populate internal structures used by `pipe`.
        """
        raise NotImplementedError(self)

    @abstractmethod
    def pipe(self) -> Collection[Writer]:
        """Return writer instances produced from the reader's parsed state."""
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        """Structural check used by `issubclass` to recognise Reader-like types."""
        return abc_subclasshook_check(
            Reader,
            cls,
            subclass,
            names=(
                "options",
                "path",
                cls.pipe.__name__,
                cls.read.__name__,
            ),
        )


class CodeLibrary(metaclass=ABCMeta):
    """Interface for readers that contain library code.

    Implementors expose a `codes` property returning sequences of code
    objects used by `MarkdownReader` when composing generated modules.
    """

    __slots__: ClassVar = ()

    @property
    @abstractmethod
    def codes(self) -> Collection[Sequence[CodeType]]:
        """Sequence(s) of compiled code objects exposed by code-library readers."""
        ...

    @classmethod
    def __subclasshook__(cls, subclass: type):
        """Structural check used by `issubclass` to recognise CodeLibrary types."""
        return abc_subclasshook_check(CodeLibrary, cls, subclass, names=("codes",))


def _Python_env(
    reader: Reader,
    modifier: (
        Callable[[ModuleType, Mapping[str, ModuleType]], AbstractContextManager[Any]]
        | None
    ) = None,
) -> Environment:
    """Create an execution environment for running extracted Python code.

    The environment ensures import isolation and provides helpers such as
    `cwf` (current working file) and `cwf_sect` to locate file sections.
    """
    if modifier is None:
        modifier = ignore_args(nullcontext)

    def cwf_sect(section: str | None):
        return (
            NULL_LOCATION
            if section is None
            else FileSection(path=reader.path, section=section)
        )

    def cwf_sects0(sections: Iterable[str | None]):
        return (cwf_sect(sect) for sect in sections)

    def cwf_sects(*sections: str | None):
        return tuple(cwf_sects0(sections))

    vars = {
        "__builtins__": {
            k: v
            for k, v in builtins.__dict__.items()
            if k not in _PYTHON_ENV_BUILTINS_EXCLUDE
        }
    }

    @asynccontextmanager
    async def context():
        loop = get_running_loop()
        async with _PYTHON_ENV_MODULE_LOCKS.setdefault(loop, cache(AsyncLock))():
            try:
                module, module_map = _PYTHON_ENV_MODULE_CACHE[loop]
            except KeyError:
                module = copy_module(import_module(".virenv", __package__))
                module_map = dict[str, ModuleType]()
                old_name = module.__name__
                for mod in deep_foreach_module(module):
                    mod.__name__ = new_name = mod.__name__.replace(old_name, NAME, 1)
                    new_name_parts = new_name.split(".")
                    new_basename = new_name_parts.pop()
                    try:
                        delattr(module_map[".".join(new_name_parts)], new_basename)
                    except KeyError:
                        pass
                    module_map[new_name] = mod
                module_map = MappingProxyType(module_map)
            try:
                with modifier(module, module_map), mock.patch.dict(modules, module_map):
                    yield
            finally:
                # Do not rely on package-level re-exports. Check package
                # configuration dirtiness via its `meta` module instead of
                # `module.dirty()` so `__init__` can remain non-exporting.
                if not import_module(".virenv.meta", __package__).dirty():
                    _PYTHON_ENV_MODULE_CACHE[loop] = (module, module_map)

    return Environment(
        env={
            "cwf": reader.path,
            "cwd": reader.path.parent,
            cwf_sect.__name__: cwf_sect,
            cwf_sects.__name__: cwf_sects,
            cwf_sects0.__name__: cwf_sects0,
        },
        globals=vars,
        locals=vars,
        context=context,
    )


@CodeLibrary.register
@Reader.register2(".md")
class MarkdownReader(Reader):
    """A `Reader` that extracts Python code blocks embedded in Markdown.

    Blocks are delimited by fenced code blocks and annotated to indicate
    whether they are `data` or `module` blocks. The reader offers a
    `pipe` method which yields configured `Writer` instances.
    """

    __slots__: ClassVar = ("__codes", "__library_codes", "__options", "__path")

    START: ClassVar = re.compile(
        rf"```Python\n# {NAME} generate (data|module)", re.NOFLAG
    )
    STOP: ClassVar = re.compile(r"```", re.NOFLAG)
    IMPORT: ClassVar = re.compile(r"# import (.+)$", re.MULTILINE)

    @property
    def path(self) -> Path:
        """Filesystem path associated with this `MarkdownReader`."""
        return self.__path

    @property
    def options(self) -> GenOpts:
        """Generation options supplied to this reader instance."""
        return self.__options

    @property
    def codes(self) -> list[Sequence[CodeType]]:
        """Return compiled module-level code blocks collected by the reader."""
        return self.__library_codes

    def __init__(self, *, path: Path, options: GenOpts) -> None:
        """Initialise a `MarkdownReader` for `path` with the given `options`."""
        self.__path = path
        self.__options = options
        self.__library_codes: list[Sequence[CodeType]] = []
        self.__codes: dict[CodeType, Sequence[CodeType]] = {}

    async def read(self, text: str, /) -> None:
        """Parse markdown input and extract embedded Python `data`/`module` blocks.

        Populates the reader's internal compiled-code caches used later by
        `pipe` to create writers.
        """
        compiler = partial(
            self.options.compiler,
            filename=self.path,
            mode="exec",
            flags=0,
            dont_inherit=True,
            optimize=0,
        )
        start = self.START.search(text)
        while start is not None:
            stop = self.STOP.search(text, start.end())
            if stop is None:
                raise ValueError(f"Unenclosure at char {start.start()}")
            code = text[start.end() : stop.start()]
            ast = Environment.transform_code(
                parse(
                    ("\n" * text.count("\n", 0, start.end())) + code,
                    self.path,
                    "exec",
                    type_comments=True,
                )
            )

            async def imports0() -> AsyncIterator[Iterator[CodeType]]:
                for imp in self.IMPORT.finditer(code):
                    reader = await Reader.cached(
                        path=self.path / imp[1], options=self.options
                    )
                    if not isinstance(reader, CodeLibrary):
                        raise TypeError(reader)
                    yield chain.from_iterable(reader.codes)

            imports = achain[CodeType].from_iterable(imports0())
            type_ = start[1]
            if type_ == "data":
                self.__codes[compiler(ast)] = await atuple(imports)
            elif type_ == "module":
                self.__library_codes.append(
                    await atuple(achain(imports, (compiler(ast),)))
                )
            else:
                raise ValueError(type_)
            start = self.START.search(text, stop.end())

    def pipe(self) -> tuple[Writer, ...]:
        """Produce `Writer` instances for each extracted code block.

        Returns a tuple of configured `Writer` objects which will execute the
        extracted code within the isolated `Environment`.
        """
        assert isinstance(self, Reader)

        @contextmanager
        def modifier(module: ModuleType, module_map: Mapping[str, ModuleType]):
            finals: list[Callable[[], None]] = []
            try:
                if self.options.init_flashcards:
                    cls: type[StatefulFlashcardGroup] = module_map[
                        f"{module.__name__}.util"
                    ].StatefulFlashcardGroup
                    old = cls.__str__

                    @wraps(old)
                    def new(self: StatefulFlashcardGroup) -> str:
                        diff: int = len(self.flashcard) - len(self.state)
                        if diff > 0:
                            self = replace(
                                self,
                                state=type(self.state)(
                                    chain(
                                        self.state,
                                        repeat(
                                            type(self.state).element_type(
                                                date=date.today(),
                                                interval=1,
                                                ease=FLASHCARD_EASE_DEFAULT,
                                            ),
                                            diff,
                                        ),
                                    )
                                ),
                            )
                        return old(self)

                    def final():
                        cls.__str__ = old

                    finals.append(final)
                    cls.__str__ = new
                yield
            finally:
                for final in finals:
                    final()

        def ret_gen():
            for code, library in self.__codes.items():
                ret = PythonWriter(
                    code,
                    init_codes=unique_everseen(chain(library, *self.codes)),
                    env=_Python_env(self, modifier),
                    options=self.options,
                )
                assert isinstance(ret, Writer)
                yield ret

        return tuple(ret_gen())


assert issubclass(MarkdownReader, Reader)
assert issubclass(MarkdownReader, CodeLibrary)
