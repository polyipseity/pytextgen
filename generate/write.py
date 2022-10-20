import abc as _abc
import contextlib as _contextlib
import datetime as _datetime
import re as _re
import types as _types
import typing as _typing

from .. import globals as _globals
from . import virenv as _virenv


class Writer(metaclass=_abc.ABCMeta):
    __slots__ = ()

    @_contextlib.contextmanager
    @_abc.abstractmethod
    def write(self: _typing.Self) -> _typing.Iterator[None]: ...

    @classmethod
    def __subclasshook__(cls: type[_typing.Self], subclass: type) -> bool | _types.NotImplementedType:
        if cls is Writer:
            if any(all(p not in c.__dict__ or c.__dict__[p] is None
                       for c in subclass.__mro__)
                   for p in (cls.write.__name__,)):
                return False
        return NotImplemented


class PythonWriter:
    __slots__ = ('__code', '__env', '__timestamp')

    def __init__(self: _typing.Self,
                 code: _typing.Any, /, *,
                 env: _virenv.Environment,
                 timestamp: bool = True) -> None:
        self.__code: _typing.Any = code
        self.__env: _virenv.Environment = env
        self.__timestamp: bool = timestamp

    def __repr__(self: _typing.Self) -> str:
        return f'{PythonWriter.__qualname__}({self.__code!r}, env={self.__env!r}, timestamp={self.__timestamp!r})'

    @_contextlib.contextmanager
    def write(self: _typing.Self) -> _typing.Iterator[None]:
        results0: _typing.Any = self.__env.exec(self.__code)
        if not isinstance(results0, _virenv.gen.Results):
            raise TypeError(results0)
        results: _virenv.gen.Results = results0
        del results0
        try:
            yield
        finally:
            result: _virenv.gen.Result
            for result in results:
                io: _typing.TextIO
                with result.location.open() as io:
                    text: str = io.read()
                    timestamp: _re.Match[str] | None = _globals.generate_comment_regex.search(
                        text)
                    if result.text != (text[:timestamp.start()] + text[timestamp.end():] if timestamp else text):
                        io.seek(0)
                        if self.__timestamp:
                            io.write(_globals.generate_comment.format(
                                now=_datetime.datetime.now().astimezone().isoformat()))
                        elif timestamp:
                            io.write(text[timestamp.start():timestamp.end()])
                        io.write(result.text)
                        io.truncate()


Writer.register(PythonWriter)
assert issubclass(PythonWriter, Writer)
