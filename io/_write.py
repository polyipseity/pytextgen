# -*- coding: UTF-8 -*-
import abc as _abc
import anyio as _anyio
import asyncio as _asyncio
import contextlib as _contextlib
import datetime as _datetime
import functools as _functools
import threading as _threading
import types as _types
import typing as _typing
import weakref as _weakref

from .. import globals as _globals
from .. import util as _util
from ._env import Environment as _Env
from ._options import Options as _Opts
from ._util import Result as _Ret, Results as _Rets

_WRITE_LOCKS = _weakref.WeakKeyDictionary[
    _anyio.Path, _typing.Callable[[], _threading.Lock]
]()


class Writer(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()

    @_abc.abstractmethod
    def write(self) -> _contextlib.AbstractAsyncContextManager[None]:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool | _types.NotImplementedType:
        return _util.abc_subclasshook_check(
            Writer, cls, subclass, names=(cls.write.__name__,)
        )


class PythonWriter:
    __slots__: _typing.ClassVar = ("__code", "__env", "__options")

    def __init__(
        self,
        code: _types.CodeType,
        /,
        *,
        env: _Env,
        options: _Opts,
    ) -> None:
        self.__code: _types.CodeType = code
        self.__env: _Env = env
        self.__options: _Opts = options

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.__code!r}, env={self.__env!r}, options={self.__options!r})"

    def __str__(self) -> str:
        return f"{type(self).__qualname__}({self.__code}, env={self.__env}, options={self.__options})"

    @_contextlib.asynccontextmanager
    async def write(self):
        results0 = await self.__env.exec(self.__code)
        if not isinstance(results0, _Rets):
            raise TypeError(results0)
        results = results0
        try:
            yield
        finally:

            async def process(result: _Ret):
                loc = result.location
                path = loc.path
                path = path if path is None else await path.resolve(strict=True)
                async with _contextlib.nullcontext() if path is None else _util.async_lock(
                    _WRITE_LOCKS.setdefault(path, _functools.cache(_threading.Lock))()
                ):
                    async with loc.open() as io:
                        text = await _util.maybe_async(io.read())
                        timestamp = _globals.GENERATE_COMMENT_REGEX.search(text)
                        if result.text != (
                            text[: timestamp.start()] + text[timestamp.end() :]
                            if timestamp
                            else text
                        ):
                            async with _asyncio.TaskGroup() as group:
                                group.create_task(_util.maybe_async(io.seek(0)))
                                data = "".join(
                                    (
                                        _globals.GENERATE_COMMENT_FORMAT.format(
                                            now=_datetime.datetime.now()
                                            .astimezone()
                                            .isoformat()
                                        )
                                        if self.__options.timestamp
                                        else text[timestamp.start() : timestamp.end()]
                                        if timestamp
                                        else "",
                                        result.text,
                                    )
                                )
                            await _util.maybe_async(io.write(data))
                            await _util.maybe_async(io.truncate())

            await _asyncio.gather(*map(process, results))


Writer.register(PythonWriter)
assert issubclass(PythonWriter, Writer)
