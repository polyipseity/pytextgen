# -*- coding: UTF-8 -*-
import abc as _abc
import ast as _ast
import asyncio as _asyncio
import builtins as _builtins
import contextlib as _contextlib
import dataclasses as _dataclasses
import datetime as _datetime
import functools as _functools
import importlib as _importlib
import itertools as _itertools
import pathlib as _pathlib
import sys as _sys
import types as _types
import typing as _typing
import unittest.mock as _unittest_mock

from .. import globals as _globals
from .. import info as _info
from .. import util as _util
from .virenv import Environment as _Env, util as _virenv_util
from ._options import Options as _Opts
from ._write import PythonWriter as _PyWriter, Writer as _Writer

_PYTHON_ENV_BUILTINS_EXCLUDE: _typing.AbstractSet[str] = frozenset(
    # constants: https://docs.python.org/library/constants.html
    # functions: https://docs.python.org/library/functions.html
)
_Python_env_module_cache: _typing.MutableMapping[
    _asyncio.AbstractEventLoop, _types.ModuleType | None
] = {}


class Reader(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()
    registry: _typing.ClassVar[_typing.MutableMapping[str, type]] = {}

    @_abc.abstractmethod
    def __init__(self, *, path: _pathlib.Path, options: _Opts) -> None:
        raise NotImplementedError(self)

    @property
    @_abc.abstractmethod
    def path(self) -> _pathlib.Path:
        raise NotImplementedError(self)

    @property
    @_abc.abstractmethod
    def options(self) -> _Opts:
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

        @_contextlib.contextmanager
        def dummy_modifier(_: _types.ModuleType):
            yield

        modifier = dummy_modifier

    async def new_module():
        loop = _asyncio.get_running_loop()
        try:
            module = _Python_env_module_cache[loop]
            while module is None:
                await _asyncio.sleep(0)
                module = _Python_env_module_cache[loop]
            _Python_env_module_cache[loop] = None
            return module
        except KeyError:
            _Python_env_module_cache[loop] = None
            module = _util.copy_module(_importlib.import_module(".virenv", __package__))
            module.__name__ = _info.NAME
            return module

    def get_module():
        return _sys.modules[_info.NAME]

    def cwf_section(section: str) -> _virenv_util.Location:
        ret: _virenv_util.FileSection = get_module().util.FileSection(
            path=reader.path, section=section
        )
        assert isinstance(
            ret,
            _typing.cast(type[_virenv_util.Location], get_module().util.Location),
        )
        return ret

    vars: _typing.MutableMapping[str, _typing.Any | None] = {
        "__builtins__": {
            k: v
            for k, v in _builtins.__dict__.items()
            if k not in _PYTHON_ENV_BUILTINS_EXCLUDE
        }
    }

    @_contextlib.asynccontextmanager
    async def context():
        module = await new_module()
        try:
            with modifier(module), _unittest_mock.patch.dict(
                _sys.modules, {_info.NAME: module}
            ):
                yield
        finally:
            loop = _asyncio.get_running_loop()
            if not module.dirty():
                _Python_env_module_cache[loop] = module
            else:
                del _Python_env_module_cache[loop]

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
    stop: _typing.ClassVar = "```"

    @property
    def path(self) -> _pathlib.Path:
        return self.__path

    @property
    def options(self) -> _Opts:
        return self.__options

    def __init__(self, *, path: _pathlib.Path, options: _Opts) -> None:
        self.__path: _pathlib.Path = path.resolve(strict=True)
        self.__options: _Opts = options
        self.__codes: _typing.MutableSequence[_types.CodeType] = []

    def read(self, text: str, /) -> None:
        start: int = text.find(self.START)
        while start != -1:
            stop: int = text.find(self.stop, start + len(self.stop))
            if stop == -1:
                raise ValueError(f"Unenclosure at char {start}")
            self.__codes.append(
                self.__options.compiler(
                    _Env.transform_code(
                        _ast.parse(
                            ("\n" * text.count("\n", 0, start + len(self.START)))
                            + text[start + len(self.START) : stop],
                            self.__path,
                            "exec",
                            type_comments=True,
                        )
                    ),
                    filename=self.__path,
                    mode="exec",
                    flags=0,
                    dont_inherit=True,
                    optimize=0,
                )
            )
            start = text.find(self.START, stop + len(self.stop))

    def pipe(self) -> _typing.Collection[_Writer]:
        assert isinstance(self, Reader)

        @_contextlib.contextmanager
        def modifier(mod: _types.ModuleType):
            finals: _typing.MutableSequence[_typing.Callable[[], None]] = []
            try:
                if self.__options.init_flashcards:
                    cls: type[
                        _virenv_util.StatefulFlashcardGroup
                    ] = mod.util.StatefulFlashcardGroup
                    old: _typing.Callable[
                        [_virenv_util.StatefulFlashcardGroup], str
                    ] = cls.__str__

                    @_functools.wraps(old)
                    def new(self: _virenv_util.StatefulFlashcardGroup) -> str:
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
                    options=self.__options,
                )
                assert isinstance(ret, _Writer)
                yield ret

        return tuple(ret_gen())


Reader.register(MarkdownReader)
assert issubclass(MarkdownReader, Reader)
Reader.registry[".md"] = MarkdownReader
