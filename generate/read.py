import abc as _abc
import ast as _ast
import builtins as _builtins
import datetime as _datetime
import functools as _functools
import importlib.machinery as _importlib_machinery
import importlib.util as _importlib_util
import itertools as _itertools
import pathlib as _pathlib
import types as _types
import typing as _typing

from .. import globals as _globals
from .. import util as _util
from . import options as _options
from . import virenv as _virenv
from .virenv import util as _virenv_util
from . import write as _write


class Reader(metaclass=_abc.ABCMeta):
    __slots__: _typing.ClassVar = ()
    registry: _typing.ClassVar[_typing.MutableMapping[str, type]] = {}

    @_abc.abstractmethod
    def __init__(self: _typing.Self, *,
                 path: _pathlib.Path,
                 options: _options.Options) -> None: ...

    @property
    @_abc.abstractmethod
    def path(self: _typing.Self) -> _pathlib.Path: ...

    @property
    @_abc.abstractmethod
    def options(self: _typing.Self) -> _options.Options: ...

    @_abc.abstractmethod
    def read(self: _typing.Self, text: str, /) -> None: ...

    @_abc.abstractmethod
    def pipe(self: _typing.Self) -> _typing.Collection[_write.Writer]: ...

    @classmethod
    def __subclasshook__(cls: type[_typing.Self], subclass: type) -> bool | _types.NotImplementedType:
        return _util.abc_subclasshook_check(Reader, cls, subclass,
                                            names=('path', 'options', cls.read.__name__, cls.pipe.__name__,))


def _Python_env(reader: Reader) -> _typing.Mapping[str, _typing.Any]:
    def cwf_section(section: str) -> _virenv_util.Location:
        return _typing.cast(_virenv_util.Location,
                            _virenv_util.FileSection(
                                path=reader.path, section=section)
                            )
    return _types.MappingProxyType({
        'cwf': reader.path,
        'cwd': reader.path.parent,
        'cwf_section': cwf_section,
    })


class MarkdownReader:
    __slots__: _typing.ClassVar = ('__path', '__codes', '__options')
    builtins_exclude: _typing.ClassVar[_typing.AbstractSet[str]] = frozenset(
        # constants: https://docs.python.org/library/constants.html
        # functions: https://docs.python.org/library/functions.html
    )
    start: _typing.ClassVar[str] = f'```Python\n# {_globals.uuid} generate data'
    stop: _typing.ClassVar[str] = '```'

    @property
    def path(self: _typing.Self) -> _pathlib.Path: return self.__path

    @property
    def options(self: _typing.Self) -> _options.Options: return self.__options

    def __init__(self: _typing.Self, *,
                 path: _pathlib.Path,
                 options: _options.Options) -> None:
        self.__path: _pathlib.Path = path.resolve(strict=True)
        self.__codes: _typing.MutableSequence[_types.CodeType] = []
        self.__options: _options.Options = options

    def read(self: _typing.Self, text: str, /) -> None:
        start: int = text.find(self.start)
        while start != -1:
            stop: int = text.find(self.stop, start + len(self.stop))
            if stop == -1:
                raise ValueError(f'Unenclosure at char {start}')
            self.__codes.append(
                compile('\n' * text.count('\n', 0, start + len(self.start))
                        + text[start + len(self.start):stop],
                        filename=self.__path,
                        mode='exec',
                        flags=_ast.PyCF_ALLOW_TOP_LEVEL_AWAIT,
                        dont_inherit=True,
                        optimize=0)
            )
            start = text.find(self.start, stop + len(self.stop))

    def pipe(self: _typing.Self) -> _typing.Collection[_write.Writer]:
        def gen_env() -> _virenv.Environment:
            spec: _importlib_machinery.ModuleSpec = _virenv.__spec__
            mod = _importlib_util.module_from_spec(spec)
            if spec.loader is None:
                raise ValueError(spec)
            spec.loader.exec_module(mod)
            if self.__options.init_flashcards:
                cls: type[_virenv_util.StatefulFlashcardGroup] = mod.util.StatefulFlashcardGroup
                old: _typing.Callable[[
                    _virenv_util.StatefulFlashcardGroup], str] = cls.__str__

                @_functools.wraps(old)
                def new(self: _virenv_util.StatefulFlashcardGroup) -> str:
                    self0: _virenv_util.StatefulFlashcardGroup = self
                    diff: int = len(self.flashcard) - len(self.state)
                    if diff > 0:
                        self0 = type(self)(
                            flashcard=self.flashcard,
                            state=type(self.state)(_itertools.chain(
                                self.state,
                                _itertools.repeat(type(self.state).element_type(
                                    date=_datetime.date.today(),
                                    interval=1,
                                    ease=_globals.flashcard_ease_default,
                                ), diff),
                            )),
                        )
                    return old(self0)
                cls.__str__ = new
            vars: _typing.MutableMapping[str, _typing.Any] = mod.__dict__
            vars['__builtins__'] = {k: v for k, v in _builtins.__dict__.items()
                                    if k not in self.builtins_exclude}
            return _virenv.Environment(
                env=_Python_env(_typing.cast(Reader, self)),
                globals=vars,
                locals=vars
            )

        def ret_gen() -> _typing.Iterator[_write.Writer]:
            code: _types.CodeType
            for code in self.__codes:
                ret: _write.PythonWriter = _write.PythonWriter(
                    code, env=gen_env(), options=self.__options)
                assert isinstance(ret, _write.Writer)
                yield ret
        return tuple(ret_gen())


Reader.register(MarkdownReader)
assert issubclass(MarkdownReader, Reader)
Reader.registry['.md'] = MarkdownReader
