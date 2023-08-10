# -*- coding: UTF-8 -*-
from .. import (
    FLASHCARD_EASE_DEFAULT as _FC_EASE_DEF,
    NAME as _NAME,
    OPEN_TEXT_OPTIONS as _OPEN_TXT_OPTS,
    UUID as _UUID,
    util as _util,
)
from .util import FileSection as _FSect
from .virenv import util as _vutil
from ._env import Environment as _Env
from ._options import GenOpts as _GenOpts
from ._write import PythonWriter as _PyWriter, Writer as _Writer
import abc as _abc
import ast as _ast
import anyio as _anyio
import asyncio as _asyncio
import asyncstdlib as _asyncstdlib
import builtins as _builtins
import collections as _collections
import contextlib as _contextlib
import dataclasses as _dataclasses
import datetime as _datetime
import functools as _functools
import importlib as _importlib
import itertools as _itertools
import more_itertools as _more_itertools
import os as _os
import re as _re
import sys as _sys
import threading as _threading
import types as _types
import typing as _typing
from unittest import mock as _unittest_mock
import weakref as _weakref

_PYTHON_ENV_BUILTINS_EXCLUDE: _typing.AbstractSet[str] = frozenset(
    # constants: https://docs.python.org/library/constants.html
    # functions: https://docs.python.org/library/functions.html
)
_PYTHON_ENV_MODULE_LOCKS = _weakref.WeakKeyDictionary[
    _asyncio.AbstractEventLoop, _typing.Callable[[], _asyncio.Lock]
]()
_PYTHON_ENV_MODULE_CACHE = _weakref.WeakKeyDictionary[
    _asyncio.AbstractEventLoop,
    tuple[_types.ModuleType, _typing.Mapping[str, _types.ModuleType]],
]()


class Reader(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()
    REGISTRY: _typing.ClassVar[_typing.MutableMapping[str, type[_typing.Self]]] = {}
    __CACHE = dict[_anyio.Path, _typing.Self]()
    __CACHE_LOCKS = _collections.defaultdict[_anyio.Path, _threading.Lock](
        _threading.Lock
    )

    @classmethod
    async def new(cls, *, path: _anyio.Path, options: _GenOpts):
        _, ext = _os.path.splitext(path)
        ret = cls.REGISTRY[ext](path=path, options=options)
        async with await path.open(mode="rt", **_OPEN_TXT_OPTS) as io:
            await ret.read(await io.read())
        return ret

    @classmethod
    async def cached(cls, *, path: _anyio.Path, options: _GenOpts):
        path = await path.resolve(strict=True)
        async with _util.async_lock(cls.__CACHE_LOCKS[path]):
            try:
                return cls.__CACHE[path]
            except KeyError:
                ret = cls.__CACHE[path] = await cls.new(path=path, options=options)
        return ret

    @_abc.abstractmethod
    def __init__(self, *, path: _anyio.Path, options: _GenOpts) -> None:
        raise NotImplementedError(self)

    @property
    @_abc.abstractmethod
    def path(self) -> _anyio.Path:
        raise NotImplementedError(self)

    @property
    @_abc.abstractmethod
    def options(self) -> _GenOpts:
        raise NotImplementedError(self)

    @_abc.abstractmethod
    async def read(self, text: str, /) -> None:
        raise NotImplementedError(self)

    @_abc.abstractmethod
    def pipe(self) -> _typing.Collection[_Writer]:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return _util.abc_subclasshook_check(
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


class CodeLibrary(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @property
    @_abc.abstractmethod
    def codes(self) -> _typing.Collection[_typing.Sequence[_types.CodeType]]:
        ...

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return _util.abc_subclasshook_check(
            CodeLibrary, cls, subclass, names=("codes",)
        )


def _Python_env(
    reader: Reader,
    modifier: _typing.Callable[
        [_types.ModuleType, _typing.Mapping[str, _types.ModuleType]],
        _contextlib.AbstractContextManager[_typing.Any],
    ]
    | None = None,
) -> _Env:
    if modifier is None:
        modifier = _util.ignore_args(_contextlib.nullcontext)

    def cwf_sect(section: str):
        return _FSect(path=reader.path, section=section)

    def cwf_sects0(sections: _typing.Iterable[str]):
        return (cwf_sect(sect) for sect in sections)

    def cwf_sects(*sections: str):
        return tuple(cwf_sects0(sections))

    vars: _typing.MutableMapping[str, _typing.Any] = {
        "__builtins__": {
            k: v
            for k, v in _builtins.__dict__.items()
            if k not in _PYTHON_ENV_BUILTINS_EXCLUDE
        }
    }

    @_contextlib.asynccontextmanager
    async def context():
        loop = _asyncio.get_running_loop()
        async with _PYTHON_ENV_MODULE_LOCKS.setdefault(
            loop, _functools.cache(_asyncio.Lock)
        )():
            try:
                module, modules = _PYTHON_ENV_MODULE_CACHE[loop]
            except KeyError:
                module = _util.copy_module(
                    _importlib.import_module(".virenv", __package__)
                )
                modules = dict[str, _types.ModuleType]()
                old_name = module.__name__
                for mod in _util.deep_foreach_module(module):
                    mod.__name__ = new_name = mod.__name__.replace(old_name, _NAME, 1)
                    new_name_parts = new_name.split(".")
                    new_basename = new_name_parts.pop()
                    try:
                        delattr(modules[".".join(new_name_parts)], new_basename)
                    except KeyError:
                        pass
                    modules[new_name] = mod
                modules = _types.MappingProxyType(modules)
            try:
                with modifier(module, modules), _unittest_mock.patch.dict(
                    _sys.modules, modules
                ):
                    yield
            finally:
                if not module.dirty():
                    _PYTHON_ENV_MODULE_CACHE[loop] = (module, modules)

    return _Env(
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


class MarkdownReader:
    __slots__: _typing.ClassVar = ("__codes", "__library_codes", "__options", "__path")

    START: _typing.ClassVar = _re.compile(
        rf"```Python\n# {_UUID} generate (data|module)", _re.NOFLAG
    )
    STOP: _typing.ClassVar = _re.compile(r"```", _re.NOFLAG)
    IMPORT: _typing.ClassVar = _re.compile(r"# import (.+)$", _re.MULTILINE)

    @property
    def path(self):
        return self.__path

    @property
    def options(self):
        return self.__options

    @property
    def codes(self):
        return self.__library_codes

    def __init__(self, *, path: _anyio.Path, options: _GenOpts) -> None:
        self.__path = path
        self.__options = options
        self.__library_codes = list[_typing.Sequence[_types.CodeType]]()
        self.__codes = dict[_types.CodeType, _typing.Sequence[_types.CodeType]]()

    async def read(self, text: str, /):
        compiler = _functools.partial(
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
            ast = _Env.transform_code(
                _ast.parse(
                    ("\n" * text.count("\n", 0, start.end())) + code,
                    self.path,
                    "exec",
                    type_comments=True,
                )
            )

            async def imports0():
                for imp in self.IMPORT.finditer(code):
                    reader = await Reader.cached(
                        path=self.path / imp[1], options=self.options
                    )
                    if not isinstance(reader, CodeLibrary):
                        raise TypeError(reader)
                    yield _itertools.chain.from_iterable(reader.codes)

            imports = _asyncstdlib.chain.from_iterable(imports0())
            type_ = start[1]
            if type_ == "data":
                self.__codes[compiler(ast)] = await _asyncstdlib.tuple(imports)
            elif type_ == "module":
                self.__library_codes.append(
                    await _asyncstdlib.tuple(
                        _asyncstdlib.chain(imports, (compiler(ast),))
                    )
                )
            else:
                raise ValueError(type_)
            start = self.START.search(text, stop.end())

    def pipe(self) -> _typing.Collection[_Writer]:
        assert isinstance(self, Reader)

        @_contextlib.contextmanager
        def modifier(
            module: _types.ModuleType, modules: _typing.Mapping[str, _types.ModuleType]
        ):
            finals: _typing.MutableSequence[_typing.Callable[[], None]] = []
            try:
                if self.options.init_flashcards:
                    cls: type[_vutil.StatefulFlashcardGroup] = modules[
                        f"{module.__name__}.util"
                    ].StatefulFlashcardGroup
                    old = cls.__str__

                    @_functools.wraps(old)
                    def new(self: _vutil.StatefulFlashcardGroup) -> str:
                        diff: int = len(self.flashcard) - len(self.state)
                        if diff > 0:
                            self = _dataclasses.replace(
                                self,
                                state=type(self.state)(
                                    _itertools.chain(
                                        self.state,
                                        _itertools.repeat(
                                            type(self.state).element_type(
                                                date=_datetime.date.today(),
                                                interval=1,
                                                ease=_FC_EASE_DEF,
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

        def ret_gen() -> _typing.Iterator[_Writer]:
            code: _types.CodeType
            for code, library in self.__codes.items():
                ret: _PyWriter = _PyWriter(
                    code,
                    init_codes=_more_itertools.unique_everseen(
                        _itertools.chain(library, *self.codes)
                    ),
                    env=_Python_env(self, modifier),
                    options=self.options,
                )
                assert isinstance(ret, _Writer)
                yield ret

        return tuple(ret_gen())


Reader.register(MarkdownReader)
assert issubclass(MarkdownReader, Reader)
CodeLibrary.register(MarkdownReader)
assert issubclass(MarkdownReader, CodeLibrary)
Reader.REGISTRY[".md"] = MarkdownReader
