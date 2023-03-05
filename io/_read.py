# -*- coding: UTF-8 -*-
import abc as _abc
import ast as _ast
import anyio as _anyio
import asyncio as _asyncio
import builtins as _builtins
import contextlib as _contextlib
import dataclasses as _dataclasses
import datetime as _datetime
import functools as _functools
import importlib as _importlib
import itertools as _itertools
import sys as _sys
import types as _types
import typing as _typing
import unittest.mock as _unittest_mock
import weakref as _weakref

from .. import globals as _globals, info as _info, util as _util
from ._env import Environment as _Env
from ._options import GenOpts as _GenOpts
from ._util import FileSection as _FSect, Location as _Loc
from ._write import PythonWriter as _PyWriter, Writer as _Writer

_PYTHON_ENV_BUILTINS_EXCLUDE: _typing.AbstractSet[str] = frozenset(
    # constants: https://docs.python.org/library/constants.html
    # functions: https://docs.python.org/library/functions.html
)
_PYTHON_ENV_MODULE_LOCKS = _weakref.WeakKeyDictionary[
    _asyncio.AbstractEventLoop, _typing.Callable[[], _asyncio.Lock]
]()
_PYTHON_ENV_MODULE_CACHE = _weakref.WeakKeyDictionary[
    _asyncio.AbstractEventLoop, _types.ModuleType
]()


class Reader(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()
    REGISTRY: _typing.ClassVar[_typing.MutableMapping[str, type[_typing.Self]]] = {}

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
    def read(self, text: str, /) -> None:
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


def _Python_env(
    reader: Reader,
    modifier: _typing.Callable[
        [_types.ModuleType], _contextlib.AbstractContextManager[_typing.Any]
    ]
    | None = None,
) -> _Env:
    if modifier is None:
        modifier = lambda _: _contextlib.nullcontext()

    def cwf_section(section: str) -> _Loc:
        ret = _FSect(path=reader.path, section=section)
        assert isinstance(ret, _Loc)
        return ret

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
                module = _PYTHON_ENV_MODULE_CACHE[loop]
            except KeyError:
                module = _util.copy_module(
                    _importlib.import_module(".virenv", __package__)
                )
                old_name = module.__name__
                for mod in _util.deep_foreach_module(module):
                    mod.__name__ = mod.__name__.replace(old_name, _info.NAME, 1)
            try:
                with modifier(module), _unittest_mock.patch.dict(
                    _sys.modules,
                    {mod.__name__: mod for mod in _util.deep_foreach_module(module)},
                ):
                    yield
            finally:
                if not module.dirty():
                    _PYTHON_ENV_MODULE_CACHE[loop] = module

    return _Env(
        env={
            "cwf": reader.path,
            "cwd": reader.path.parent,
            "cwf_section": cwf_section,
        },
        globals=vars,
        locals=vars,
        context=context,
    )


class MarkdownReader:
    __slots__: _typing.ClassVar = ("__codes", "__options", "__path")

    START: _typing.ClassVar = f"```Python\n# {_globals.UUID} generate data"
    STOP: _typing.ClassVar = "```"

    @property
    def path(self):
        return self.__path

    @property
    def options(self) -> _GenOpts:
        return self.__options

    def __init__(self, *, path: _anyio.Path, options: _GenOpts) -> None:
        self.__path = path
        self.__options: _GenOpts = options
        self.__codes: _typing.MutableSequence[_types.CodeType] = []

    def read(self, text: str, /) -> None:
        start: int = text.find(self.START)
        while start != -1:
            stop: int = text.find(self.STOP, start + len(self.STOP))
            if stop == -1:
                raise ValueError(f"Unenclosure at char {start}")
            self.__codes.append(
                self.options.compiler(
                    _Env.transform_code(
                        _ast.parse(
                            ("\n" * text.count("\n", 0, start + len(self.START)))
                            + text[start + len(self.START) : stop],
                            self.path,
                            "exec",
                            type_comments=True,
                        )
                    ),
                    filename=self.path,
                    mode="exec",
                    flags=0,
                    dont_inherit=True,
                    optimize=0,
                )
            )
            start = text.find(self.START, stop + len(self.STOP))

    def pipe(self) -> _typing.Collection[_Writer]:
        assert isinstance(self, Reader)

        @_contextlib.contextmanager
        def modifier(mod: _types.ModuleType):
            finals: _typing.MutableSequence[_typing.Callable[[], None]] = []
            try:
                if self.options.init_flashcards:
                    cls: type[object] = mod.util.StatefulFlashcardGroup
                    old = cls.__str__

                    @_functools.wraps(old)
                    def new(self: _typing.Any) -> str:
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
                                                ease=_globals.FLASHCARD_EASE_DEFAULT,
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
            for code in self.__codes:
                ret: _PyWriter = _PyWriter(
                    code,
                    env=_Python_env(self, modifier),
                    options=self.options,
                )
                assert isinstance(ret, _Writer)
                yield ret

        return tuple(ret_gen())


Reader.register(MarkdownReader)
assert issubclass(MarkdownReader, Reader)
Reader.REGISTRY[".md"] = MarkdownReader
