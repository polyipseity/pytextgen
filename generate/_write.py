# -*- coding: UTF-8 -*-
import abc as _abc
import contextlib as _contextlib
import datetime as _datetime
import re as _re
import types as _types
import typing as _typing

from .. import globals as _globals
from .. import util as _util
from .virenv import gen as _virenv_gen
from ._options import *
import virenv as _virenv


class Writer(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_contextlib.contextmanager
    @_abc.abstractmethod
    def write(self: _typing.Self) -> _typing.Iterator[None]:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(
        cls: type[_typing.Self], subclass: type
    ) -> bool | _types.NotImplementedType:
        return _util.abc_subclasshook_check(
            Writer, cls, subclass, names=(cls.write.__name__,)
        )


class PythonWriter:
    __slots__: _typing.ClassVar = ("__code", "__env", "__options")

    def __init__(
        self: _typing.Self,
        code: _types.CodeType,
        /,
        *,
        env: _virenv.Environment,
        options: Options,
    ) -> None:
        self.__code: _types.CodeType = code
        self.__env: _virenv.Environment = env
        self.__options: Options = options

    def __repr__(self: _typing.Self) -> str:
        return f"{type(self).__qualname__}({self.__code!r}, env={self.__env!r}, options={self.__options!r})"

    def __str__(self: _typing.Self) -> str:
        return f"{type(self).__qualname__}({self.__code}, env={self.__env}, options={self.__options})"

    @_contextlib.contextmanager
    def write(self: _typing.Self) -> _typing.Iterator[None]:
        results0: _typing.Any | None = self.__env.exec(self.__code)
        if not isinstance(results0, _virenv_gen.Results):
            raise TypeError(results0)
        results: _virenv_gen.Results = results0
        del results0
        try:
            yield
        finally:
            result: _virenv_gen.Result
            for result in results:
                io: _typing.TextIO
                with result.location.open() as io:
                    text: str = io.read()
                    timestamp: _re.Match[
                        str
                    ] | None = _globals.generate_comment_regex.search(text)
                    if result.text != (
                        text[: timestamp.start()] + text[timestamp.end() :]
                        if timestamp
                        else text
                    ):
                        io.seek(0)
                        if self.__options.timestamp:
                            io.write(
                                _globals.generate_comment_format.format(
                                    now=_datetime.datetime.now()
                                    .astimezone()
                                    .isoformat()
                                )
                            )
                        elif timestamp:
                            io.write(text[timestamp.start() : timestamp.end()])
                        io.write(result.text)
                        io.truncate()


Writer.register(PythonWriter)
assert issubclass(PythonWriter, Writer)
