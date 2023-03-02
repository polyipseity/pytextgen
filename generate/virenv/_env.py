# -*- coding: UTF-8 -*-
import ast as _ast
import contextlib as _contextlib
import types as _types
import typing as _typing

from ... import globals as _globals
from .util import maybe_async as _masync


@_typing.final
class Environment:
    ENTRY: _typing.ClassVar = f"_{_globals.UUID.replace('-', '_')}"
    ENTRY_TEMPLATE: _typing.ClassVar = f"""async def {ENTRY}(): pass
__env__.{ENTRY} = {ENTRY}"""
    __slots__: _typing.ClassVar = (
        "__closure",
        "__context",
        "__env",
        "__globals",
        "__locals",
    )

    @classmethod
    def transform_code(cls, ast: _ast.Module):
        template = _ast.parse(
            cls.ENTRY_TEMPLATE, "<string>", "exec", type_comments=True
        )
        _typing.cast(_ast.AsyncFunctionDef, template.body[0]).body = ast.body
        return template

    def __init__(
        self,
        *,
        env: _typing.Mapping[str, _typing.Any] = {},
        globals: _typing.Mapping[str, _typing.Any] = globals(),
        locals: _typing.Mapping[str, object] = locals(),
        closure: tuple[_types.CellType, ...] | None = None,
        context: _typing.Callable[
            [], _contextlib.AbstractAsyncContextManager[_typing.Any]
        ]
        | None = None,
    ) -> None:
        self.__env = _types.MappingProxyType(dict(env))
        self.__globals = _types.MappingProxyType(dict(globals))
        self.__locals = _types.MappingProxyType(dict(locals))
        self.__closure = closure
        if context is None:

            @_contextlib.asynccontextmanager
            async def dummy_context():
                yield

            self.__context = dummy_context
        else:
            self.__context = context
        assert "__env__" not in self.__globals
        assert "__env__" not in self.__locals

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(env={self.__env!r}, globals={self.__globals!r}, locals={self.__locals!r})"

    def __str__(self) -> str:
        def filter(map: _typing.Mapping[str, _typing.Any]):
            return {
                key: val
                for key, val in map.items()
                if not (key.startswith("__") and key.endswith("__"))
            }

        return repr(
            Environment(
                env=filter(self.env),
                globals=filter(self.globals),
                locals=filter(self.locals),
            )
        )

    @property
    def env(self) -> _typing.Mapping[str, _typing.Any]:
        return self.__env

    @property
    def globals(self) -> _typing.Mapping[str, _typing.Any]:
        return self.__globals

    @property
    def locals(self) -> _typing.Mapping[str, object]:
        return self.__locals

    async def exec(self, code: _types.CodeType) -> _typing.Any:
        env = _types.SimpleNamespace(result=None, **self.__env)
        globals = {**self.__globals, "__env__": env}
        locals = (
            globals
            if self.__locals == self.__globals
            else {**self.__locals, "__env__": env}
        )
        async with self.__context():
            exec(code, globals, locals, closure=self.__closure)
            return await _masync(getattr(env, self.ENTRY)())
