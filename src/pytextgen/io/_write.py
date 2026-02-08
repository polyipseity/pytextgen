from abc import ABCMeta as _ABCM
from abc import abstractmethod as _amethod
from asyncio import create_task
from asyncio import gather as _gather
from contextlib import (
    AbstractAsyncContextManager as _AACtxMgr,
)
from contextlib import (
    asynccontextmanager as _actxmgr,
)
from contextlib import (
    nullcontext as _nullctx,
)
from datetime import datetime as _datetime
from re import compile as _re_comp
from types import CodeType as _Code
from typing import Any as _Any
from typing import ClassVar as _ClsVar
from typing import Iterable as _Iter

from anyio import Path as _Path

from .. import (
    FLASHCARD_STATES_REGEX as _FC_ST_RE,
)
from .. import (
    GENERATE_COMMENT_FORMAT as _GEN_CMT_FMT,
)
from .. import (
    GENERATE_COMMENT_REGEX as _GEN_CMT_RE,
)
from ..io import ClearOpts as _ClrOpts
from ..io import ClearType as _ClrT
from ..io import GenOpts as _GenOpts
from ..util import abc_subclasshook_check as _abc_sch_chk
from ..util import wrap_async as _wrap_a
from ._env import Environment as _Env
from ._options import GenOpts as _GenOpts
from .util import (
    AnyTextIO as _ATxtIO,
)
from .util import (
    FileSection as _FSect,
)
from .util import (
    Result as _Ret,
)
from .util import (
    lock_file as _lck_f,
)


class Writer(metaclass=_ABCM):
    __slots__: _ClsVar = ()

    @_amethod
    def write(self) -> _AACtxMgr[None]:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        return _abc_sch_chk(Writer, cls, subclass, names=(cls.write.__name__,))


@Writer.register
class ClearWriter:
    __slots__: _ClsVar = ("__options", "__path")
    __FLASHCARD_STATES_REGEX: _ClsVar = _re_comp(
        r" ?" + _FC_ST_RE.pattern, _FC_ST_RE.flags
    )

    def __init__(self, path: _Path, *, options: _ClrOpts):
        self.__path = path
        self.__options = options

    @_actxmgr
    async def write(self):
        if _ClrT.CONTENT in self.__options.types:

            async def process(io: _ATxtIO):
                await _wrap_a(io.truncate())

        elif _ClrT.FLASHCARD_STATE in self.__options.types:

            async def process(io: _ATxtIO):
                read = await _wrap_a(io.read())
                seek = create_task(_wrap_a(io.seek(0)))
                try:
                    if (text := self.__FLASHCARD_STATES_REGEX.sub("", read)) != read:
                        await seek
                        await _wrap_a(io.write(text))
                        await _wrap_a(io.truncate())
                finally:
                    seek.cancel()

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


assert issubclass(ClearWriter, Writer)


@Writer.register
class PythonWriter:
    __slots__: _ClsVar = ("__code", "__env", "__init_codes", "__options")

    def __init__(
        self,
        code: _Code,
        /,
        *,
        init_codes: _Iter[_Code],
        env: _Env,
        options: _GenOpts,
    ):
        self.__code = code
        self.__init_codes = tuple(init_codes)
        self.__env = env
        self.__options = options

    def __repr__(self):
        return f"{type(self).__qualname__}({self.__code!r}, env={self.__env!r}, options={self.__options!r})"

    def __str__(self):
        return f"{type(self).__qualname__}({self.__code}, env={self.__env}, options={self.__options})"

    @_actxmgr
    async def write(self):
        def results0(result: _Any):
            if _Ret.isinstance(result):
                yield result
                return
            if isinstance(result, _Iter):
                result0: _Iter[_Any] = result
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
                async with _nullctx() if path is None else _lck_f(path):
                    async with loc.open() as io:
                        read = await _wrap_a(io.read())
                        seek = create_task(_wrap_a(io.seek(0)))
                        try:
                            timestamp = _GEN_CMT_RE.search(read)
                            if result.text != (
                                read[: timestamp.start()] + read[timestamp.end() :]
                                if timestamp
                                else read
                            ):
                                text = (
                                    _GEN_CMT_FMT.format(
                                        now=_datetime.now().astimezone().isoformat()
                                    )
                                    if self.__options.timestamp
                                    else timestamp[0]
                                    if timestamp
                                    else ""
                                ) + result.text
                                await seek
                                await _wrap_a(io.write(text))
                                await _wrap_a(io.truncate())
                        finally:
                            seek.cancel()

            await _gather(*map(process, results))


assert issubclass(PythonWriter, Writer)
