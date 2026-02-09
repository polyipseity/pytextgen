from abc import ABCMeta as _ABCM
from abc import abstractmethod as _amethod
from ast import parse as _parse
from asyncio import (
    AbstractEventLoop as _AEvtLoop,
)
from asyncio import (
    Lock as _ALock,
)
from asyncio import (
    get_running_loop as _run_loop,
)
from builtins import __dict__ as _builtins_dict
from collections import defaultdict as _defdict
from contextlib import (
    AbstractContextManager as _ACtxMgr,
)
from contextlib import (
    asynccontextmanager as _actxmgr,
)
from contextlib import (
    contextmanager as _ctxmgr,
)
from contextlib import (
    nullcontext as _nullctx,
)
from dataclasses import replace as _dc_repl
from datetime import date as _date
from functools import cache as _cache
from functools import partial as _partial
from functools import wraps as _wraps
from importlib import import_module as _import
from itertools import chain as _chain
from itertools import repeat as _repeat
from os.path import splitext as _splitext
from re import MULTILINE as _MULTILINE
from re import NOFLAG as _NOFLAG
from re import compile as _re_comp
from sys import modules as _mods
from threading import Lock as _TLock
from types import CodeType as _Code
from types import MappingProxyType as _FrozenMap
from types import ModuleType as _Mod
from typing import (
    Any as _Any,
)
from typing import (
    AsyncIterator as _AItor,
)
from typing import (
    Callable as _Call,
)
from typing import (
    ClassVar as _ClsVar,
)
from typing import (
    Collection as _Collect,
)
from typing import (
    Iterable as _Iter,
)
from typing import (
    Iterator as _Itor,
)
from typing import (
    Mapping as _Map,
)
from typing import (
    Self as _Self,
)
from typing import (
    Sequence as _Seq,
)
from unittest import mock as _mock
from weakref import WeakKeyDictionary as _WkKDict

from anyio import Path as _Path
from asyncstdlib import chain as _achain
from asyncstdlib import tuple as _atuple
from more_itertools import unique_everseen as _unq_eseen

from .. import FLASHCARD_EASE_DEFAULT as _FC_EASE_DEF
from .. import NAME as _NAME
from .. import OPEN_TEXT_OPTIONS as _OPEN_TXT_OPTS
from ..util import (
    abc_subclasshook_check as _abc_sch_chk,
)
from ..util import (
    async_lock as _a_lock,
)
from ..util import (
    copy_module as _cpy_mod,
)
from ..util import (
    deep_foreach_module as _deep_foreach_mod,
)
from ..util import (
    ignore_args as _i_args,
)
from ._env import Environment as _Env
from ._options import GenOpts as _GenOpts
from ._write import PythonWriter as _PyWriter
from ._write import Writer as _Writer
from .util import NULL_LOCATION as _NULL_LOC
from .util import FileSection as _FSect
from .virenv.util import StatefulFlashcardGroup as _StFcGrp

_PYTHON_ENV_BUILTINS_EXCLUDE = frozenset[str](
    # constants: https://docs.python.org/library/constants.html
    # functions: https://docs.python.org/library/functions.html
)
_PYTHON_ENV_MODULE_LOCKS = _WkKDict[_AEvtLoop, _Call[[], _ALock]]()
_PYTHON_ENV_MODULE_CACHE = _WkKDict[
    _AEvtLoop,
    tuple[_Mod, _Map[str, _Mod]],
]()


class Reader(metaclass=_ABCM):
    __slots__: _ClsVar = ()
    REGISTRY: _ClsVar = dict[str, type[_Self]]()
    __CACHE: _ClsVar = dict[_Path, _Self]()
    __CACHE_LOCKS: _ClsVar = _defdict[_Path, _TLock](_TLock)

    @classmethod
    def register2(cls, *extensions: str):
        @_wraps(cls.register)
        def register(subclass: type[_Self]) -> type[_Self]:
            ret = cls.register(subclass)
            for ext in extensions:
                cls.REGISTRY[ext] = subclass
            return ret

        return register

    @classmethod
    async def new(cls, *, path: _Path, options: _GenOpts):
        _, ext = _splitext(path)
        ret = cls.REGISTRY[ext](path=path, options=options)
        async with await path.open(mode="rt", **_OPEN_TXT_OPTS) as io:
            await ret.read(await io.read())
        return ret

    @classmethod
    async def cached(cls, *, path: _Path, options: _GenOpts):
        path = await path.resolve(strict=True)
        async with _a_lock(cls.__CACHE_LOCKS[path]):
            try:
                return cls.__CACHE[path]
            except KeyError:
                ret = cls.__CACHE[path] = await cls.new(path=path, options=options)
        return ret

    @_amethod
    def __init__(self, *, path: _Path, options: _GenOpts):
        raise NotImplementedError(self)

    @property
    @_amethod
    def path(self) -> _Path:
        raise NotImplementedError(self)

    @property
    @_amethod
    def options(self) -> _GenOpts:
        raise NotImplementedError(self)

    @_amethod
    async def read(self, text: str, /) -> None:
        raise NotImplementedError(self)

    @_amethod
    def pipe(self) -> _Collect[_Writer]:
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        return _abc_sch_chk(
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


class CodeLibrary(metaclass=_ABCM):
    __slots__: _ClsVar = ()

    @property
    @_amethod
    def codes(self) -> _Collect[_Seq[_Code]]: ...

    @classmethod
    def __subclasshook__(cls, subclass: type):
        return _abc_sch_chk(CodeLibrary, cls, subclass, names=("codes",))


def _Python_env(
    reader: Reader,
    modifier: (
        _Call[
            [_Mod, _Map[str, _Mod]],
            _ACtxMgr[_Any],
        ]
        | None
    ) = None,
):
    if modifier is None:
        modifier = _i_args(_nullctx)

    def cwf_sect(section: str | None):
        return (
            _NULL_LOC if section is None else _FSect(path=reader.path, section=section)
        )

    def cwf_sects0(sections: _Iter[str | None]):
        return (cwf_sect(sect) for sect in sections)

    def cwf_sects(*sections: str | None):
        return tuple(cwf_sects0(sections))

    vars = {
        "__builtins__": {
            k: v
            for k, v in _builtins_dict.items()
            if k not in _PYTHON_ENV_BUILTINS_EXCLUDE
        }
    }

    @_actxmgr
    async def context():
        loop = _run_loop()
        async with _PYTHON_ENV_MODULE_LOCKS.setdefault(loop, _cache(_ALock))():
            try:
                module, modules = _PYTHON_ENV_MODULE_CACHE[loop]
            except KeyError:
                module = _cpy_mod(_import(".virenv", __package__))
                modules = dict[str, _Mod]()
                old_name = module.__name__
                for mod in _deep_foreach_mod(module):
                    mod.__name__ = new_name = mod.__name__.replace(old_name, _NAME, 1)
                    new_name_parts = new_name.split(".")
                    new_basename = new_name_parts.pop()
                    try:
                        delattr(modules[".".join(new_name_parts)], new_basename)
                    except KeyError:
                        pass
                    modules[new_name] = mod
                modules = _FrozenMap(modules)
            try:
                with modifier(module, modules), _mock.patch.dict(_mods, modules):
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


@CodeLibrary.register
@Reader.register2(".md")
class MarkdownReader(Reader):
    __slots__: _ClsVar = ("__codes", "__library_codes", "__options", "__path")

    START: _ClsVar = _re_comp(rf"```Python\n# {_NAME} generate (data|module)", _NOFLAG)
    STOP: _ClsVar = _re_comp(r"```", _NOFLAG)
    IMPORT: _ClsVar = _re_comp(r"# import (.+)$", _MULTILINE)

    @property
    def path(self):
        return self.__path

    @property
    def options(self):
        return self.__options

    @property
    def codes(self):
        return self.__library_codes

    def __init__(self, *, path: _Path, options: _GenOpts):
        self.__path = path
        self.__options = options
        self.__library_codes = list[_Seq[_Code]]()
        self.__codes = dict[_Code, _Seq[_Code]]()

    async def read(self, text: str, /):
        compiler = _partial(
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
                _parse(
                    ("\n" * text.count("\n", 0, start.end())) + code,
                    self.path,
                    "exec",
                    type_comments=True,
                )
            )

            async def imports0() -> _AItor[_Itor[_Code]]:
                for imp in self.IMPORT.finditer(code):
                    reader = await Reader.cached(
                        path=self.path / imp[1], options=self.options
                    )
                    if not isinstance(reader, CodeLibrary):
                        raise TypeError(reader)
                    yield _chain.from_iterable(reader.codes)

            imports: _achain[_Code] = _achain.from_iterable(imports0())  # type: ignore[reportUnknownMemberType,reportUnknownVariableType]
            type_ = start[1]
            if type_ == "data":
                self.__codes[compiler(ast)] = await _atuple(imports)
            elif type_ == "module":
                self.__library_codes.append(
                    await _atuple(_achain(imports, (compiler(ast),)))
                )
            else:
                raise ValueError(type_)
            start = self.START.search(text, stop.end())

    def pipe(self):
        assert isinstance(self, Reader)

        @_ctxmgr
        def modifier(module: _Mod, modules: _Map[str, _Mod]):
            finals = list[_Call[[], None]]()
            try:
                if self.options.init_flashcards:
                    cls: type[_StFcGrp] = modules[
                        f"{module.__name__}.util"
                    ].StatefulFlashcardGroup
                    old = cls.__str__

                    @_wraps(old)
                    def new(self: _StFcGrp) -> str:
                        diff: int = len(self.flashcard) - len(self.state)
                        if diff > 0:
                            self = _dc_repl(
                                self,
                                state=type(self.state)(
                                    _chain(
                                        self.state,
                                        _repeat(
                                            type(self.state).element_type(
                                                date=_date.today(),
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

        def ret_gen():
            for code, library in self.__codes.items():
                ret = _PyWriter(
                    code,
                    init_codes=_unq_eseen(_chain(library, *self.codes)),
                    env=_Python_env(self, modifier),
                    options=self.options,
                )
                assert isinstance(ret, _Writer)
                yield ret

        return tuple(ret_gen())


assert issubclass(MarkdownReader, Reader)
assert issubclass(MarkdownReader, CodeLibrary)
