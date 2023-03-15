# -*- coding: UTF-8 -*-
import abc as _abc
import anyio as _anyio
import asyncio as _asyncio
import contextlib as _contextlib
import datetime as _datetime
import re as _re
import types as _types
import typing as _typing

from .. import globals as _globals, util as _util
from .util import (
    FileSection as _FSect,
    AnyTextIO as _ATxtIO,
    Result as _Ret,
    lock_file as _lck_f,
)
from ._env import Environment as _Env
from ._options import ClearOpts as _ClrOpts, ClearType as _ClrT, GenOpts as _GenOpts


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


class ClearWriter:
    __slots__: _typing.ClassVar = ("__options", "__path")
    __FLASHCARD_STATES_REGEX = _re.compile(
        r" ?" + _globals.FLASHCARD_STATES_REGEX.pattern,
        _globals.FLASHCARD_STATES_REGEX.flags,
    )

    def __init__(self, path: _anyio.Path, *, options: _ClrOpts):
        self.__path = path
        self.__options = options

    @_contextlib.asynccontextmanager
    async def write(self):
        if _ClrT.CONTENT in self.__options.types:

            async def process(io: _ATxtIO):
                await _util.wrap_async(io.truncate())

        elif _ClrT.FLASHCARD_STATE in self.__options.types:

            async def process(io: _ATxtIO):
                data = await _util.wrap_async(io.read())
                async with _asyncio.TaskGroup() as group:
                    group.create_task(_util.wrap_async(io.seek(0)).__await__())
                    data = self.__FLASHCARD_STATES_REGEX.sub("", data)
                await _util.wrap_async(io.write(data))
                await _util.wrap_async(io.truncate())

        else:

            async def process(io: _ATxtIO):
                pass

        try:
            yield
        finally:
            async with _lck_f(self.__path):
                for section in await _FSect.find(self.__path):
                    async with _FSect(path=self.__path, section=section).open() as io:
                        await process(io)


Writer.register(ClearWriter)
assert issubclass(ClearWriter, Writer)


class PythonWriter:
    __slots__: _typing.ClassVar = ("__code", "__env", "__init_codes", "__options")

    def __init__(
        self,
        code: _types.CodeType,
        /,
        *,
        init_codes: _typing.Iterable[_types.CodeType],
        env: _Env,
        options: _GenOpts,
    ) -> None:
        self.__code = code
        self.__init_codes = tuple(init_codes)
        self.__env = env
        self.__options = options

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.__code!r}, env={self.__env!r}, options={self.__options!r})"

    def __str__(self) -> str:
        return f"{type(self).__qualname__}({self.__code}, env={self.__env}, options={self.__options})"

    @_contextlib.asynccontextmanager
    async def write(self):
        def results0(result: _typing.Any):
            if _Ret.isinstance(result):
                yield result
                return
            if isinstance(result, _typing.Iterable):
                result0: _typing.Iterable[_typing.Any] = result
                for item in result0:
                    if not _Ret.isinstance(item):
                        raise TypeError(item)
                    yield item
                return
            raise TypeError(result)

        results = results0(await self.__env.exec(self.__code, *self.__init_codes))
        try:
            yield
        finally:

            async def process(result: _Ret):
                loc = result.location
                path = loc.path
                async with _contextlib.nullcontext() if path is None else _lck_f(path):
                    async with loc.open() as io:
                        text = await _util.wrap_async(io.read())
                        timestamp = _globals.GENERATE_COMMENT_REGEX.search(text)
                        if result.text != (
                            text[: timestamp.start()] + text[timestamp.end() :]
                            if timestamp
                            else text
                        ):
                            async with _asyncio.TaskGroup() as group:
                                group.create_task(
                                    _util.wrap_async(io.seek(0)).__await__()
                                )
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
                            await _util.wrap_async(io.write(data))
                            await _util.wrap_async(io.truncate())

            await _asyncio.gather(*map(process, results))


Writer.register(PythonWriter)
assert issubclass(PythonWriter, Writer)
