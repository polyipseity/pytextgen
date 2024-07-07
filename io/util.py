# -*- coding: UTF-8 -*-
from aioshutil import sync_to_async
from .. import NAME as _NAME, OPEN_TEXT_OPTIONS as _OPEN_TXT_OPTS
from ..util import (
    abc_subclasshook_check as _abc_sch_chk,
    async_lock as _a_lock,
    wrap_async as _wrap_a,
)
from abc import ABCMeta as _ABCM, abstractmethod as _amethod
from anyio import AsyncFile as _AFile, Path as _Path
from asyncio import TaskGroup, create_task
from collections import defaultdict as _defdict
from contextlib import (
    AbstractAsyncContextManager as _AACtxMgr,
    asynccontextmanager as _actxmgr,
)
from dataclasses import dataclass as _dc
from functools import cache as _cache
from io import StringIO as _StrIO
from itertools import islice as _islice
from os import stat as _stat
from os.path import splitext as _splitext
from re import (
    DOTALL as _DOTALL,
    Match as _Match,
    NOFLAG as _NOFLAG,
    Pattern as _Pattern,
    compile as _re_comp,
)
from threading import Lock as _TLock
from types import MappingProxyType as _FrozenMap, TracebackType as _Tb
from typing import (
    Any as _Any,
    Awaitable as _Await,
    Callable as _Call,
    ClassVar as _ClsVar,
    Mapping as _Map,
    Self as _Self,
    TextIO as _TxtIO,
    TypeGuard as _TGuard,
    final as _fin,
)
from weakref import WeakKeyDictionary as _WkKDict

AnyTextIO = _TxtIO | _AFile[str]
_FILE_LOCKS = _defdict[_Path, _TLock](_TLock)
_stat_a = sync_to_async(_stat)


@_actxmgr
async def lock_file(path: _Path):
    async with _a_lock(_FILE_LOCKS[await path.resolve(strict=True)]):
        yield


class Location(metaclass=_ABCM):
    __slots__: _ClsVar = ()

    @_amethod
    def open(self) -> _AACtxMgr[AnyTextIO]:
        raise NotImplementedError(self)

    @property
    @_amethod
    def path(self) -> _Path | None:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        return _abc_sch_chk(Location, cls, subclass, names=("path", cls.open.__name__))


@_fin
@Location.register
class NullLocation:
    __slots__: _ClsVar = ()

    @_actxmgr
    async def open(self):
        yield _StrIO()

    @property
    def path(self):
        return None


assert issubclass(NullLocation, Location)
NULL_LOCATION = NullLocation()


@_fin
@Location.register
@_dc(
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
class PathLocation:
    path: _Path

    @_actxmgr
    async def open(self):
        async with await self.path.open(mode="r+t", **_OPEN_TXT_OPTS) as file:
            yield file


assert issubclass(PathLocation, Location)


@_fin
@Location.register
@_dc(
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
class FileSection:
    @_fin
    @_dc(
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
    class SectionFormat:
        start_regex: _Pattern[str]
        end_regex: _Pattern[str]
        start: str
        stop: str
        data: _Call[[_Match[str]], str]

    SECTION_FORMATS: _ClsVar = {
        "": SectionFormat(
            start_regex=_re_comp(rf"\[{_NAME},generate,([^,\]]*?)\]", _NOFLAG),
            end_regex=_re_comp(rf"\[{_NAME},end\]", _NOFLAG),
            start=f"[{_NAME},generate,{{section}}]",
            stop=f"[{_NAME},end]",
            data=lambda match: match[1],
        ),
        ".md": SectionFormat(
            start_regex=_re_comp(
                rf"""<!--{_NAME} generate section=(["'])(.*?)\1-->""", _DOTALL
            ),
            end_regex=_re_comp(rf"<!--/{_NAME}-->", _NOFLAG),
            start=f'<!--{_NAME} generate section="{{section}}"-->',
            stop=f"<!--/{_NAME}-->",
            data=lambda match: match[2],
        ),
    }

    path: _Path
    section: str

    @classmethod
    async def find(cls, path: _Path):
        return (await _FILE_SECTION_CACHE[path]).sections.keys()

    @_actxmgr
    async def open(self):
        async with (
            _FileSectionIO(self)
            if self.section
            else await self.path.open(mode="r+t", **_OPEN_TXT_OPTS)
        ) as file:
            yield file


@_fin
@_dc(
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
class _FileSectionCacheData:
    EMPTY: _ClsVar[_Self]
    mod_time: int
    sections: _Map[str, tuple[slice, str]]

    def __post_init__(self):
        object.__setattr__(self, "sections", _FrozenMap(dict(self.sections)))


_FileSectionCacheData.EMPTY = _FileSectionCacheData(mod_time=-1, sections={})


class _FileSectionCache(dict[_Path, _Await[_FileSectionCacheData]]):
    __slots__: _ClsVar = ("__locks",)

    def __init__(self):
        super().__init__()
        self.__locks = _WkKDict[_Path, _Call[[], _TLock]]()

    async def __getitem__(self, key: _Path):
        key = await key.resolve(strict=True)
        _, ext = _splitext(key)
        try:
            format = FileSection.SECTION_FORMATS[ext]
        except KeyError as ex:
            raise ValueError(f"Unknown extension: {key}") from ex
        async with _a_lock(self.__locks.setdefault(key, _cache(_TLock))()):
            try:
                cache = await super().__getitem__(key)
            except KeyError:
                cache = _FileSectionCacheData.EMPTY
            try:
                mod_time = (await _stat_a(key)).st_mtime_ns
                if mod_time != cache.mod_time:
                    async with await key.open(mode="rt", **_OPEN_TXT_OPTS) as file:
                        text = await file.read()
                    sections = dict[str, tuple[slice, str]]()
                    read_to = 0
                    for start in format.start_regex.finditer(text):
                        start_idx = start.start()
                        if start.start() < read_to:
                            raise ValueError(
                                f"Overlapping section at char {start.start()}: {key}"
                            )
                        section = format.data(start)
                        if section in sections:
                            raise ValueError(f'Duplicated section "{section}": {key}')
                        end_str = format.stop.format(section=section)
                        try:
                            end_idx = text.index(end_str, start.end())
                        except ValueError as ex:
                            raise ValueError(
                                f"Unenclosure from char {start.start()}: {key}"
                            ) from ex
                        slice0 = slice(start_idx + len(start[0]), end_idx)
                        sections[section] = (slice0, text[slice0])
                        read_to = end_idx + len(end_str)
                    for end in _islice(
                        format.end_regex.finditer(text), len(sections), None
                    ):
                        raise ValueError(
                            f"Too many closings at char {end.start()}: {key}"
                        )
                    cache = _FileSectionCacheData(
                        mod_time=mod_time,
                        sections=sections,
                    )
            finally:
                super().__setitem__(key, _wrap_a(cache))  # Replenish awaitable
        return cache

    def __setitem__(self, key: _Path, value: _Await[_FileSectionCacheData]):
        raise TypeError("Unsupported")


_FILE_SECTION_CACHE = _FileSectionCache()


@_fin
class _FileSectionIO(_StrIO):
    __slots__: _ClsVar = ("__closure", "__file", "__slice", "__initial_value")

    def __init__(self, closure: FileSection, /):
        self.__closure = closure

    def __enter__(self):
        raise TypeError("Unsupported")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _Tb | None,
    ):
        raise TypeError("Unsupported")

    def close(self):
        raise TypeError("Unsupported")

    async def aclose(self):
        try:
            try:

                async def reader():
                    await self.__file.seek(0)
                    return await self.__file.read()

                read_task = create_task(reader())
                try:
                    self.seek(0)
                    if (text := self.read()) != self.__initial_value:
                        read = await read_task
                        async with TaskGroup() as tg:
                            _ = tg.create_task(self.__file.seek(0))
                            text = f"{read[: self.__slice.start]}{text}{read[self.__slice.stop :]}"
                        await self.__file.write(text)
                        await self.__file.truncate()
                finally:
                    read_task.cancel()
            finally:
                await self.__file.aclose()
        finally:
            super().close()

    async def __aenter__(self):
        self.__file = await self.__closure.path.open(mode="r+t", **_OPEN_TXT_OPTS)
        try:
            self.__slice, self.__initial_value = (
                await _FILE_SECTION_CACHE[self.__closure.path]
            ).sections[self.__closure.section]
            super().__init__(self.__initial_value)
            super().__enter__()
        except Exception:
            await self.__file.aclose()
            raise
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: _Tb | None,
    ):
        await self.aclose()


assert issubclass(FileSection, Location)


@_fin
@_dc(
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
class Result:
    location: Location
    text: str

    @classmethod
    def isinstance(cls, any: _Any) -> _TGuard[_Self]:
        try:
            return isinstance(any.location, Location) and isinstance(any.text, str)
        except AttributeError:
            return False
