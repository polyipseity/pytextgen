"""Execution environment used to run extracted Python code safely.

`Environment` prepares isolated globals/locals and supports an async
initialization step to return exported values from executed code.
"""

from ast import AsyncFunctionDef, Module, parse
from contextlib import AbstractAsyncContextManager, nullcontext
from types import CellType, CodeType, MappingProxyType, SimpleNamespace
from typing import Any, Callable, ClassVar, Mapping, cast, final

from ..meta import UUID

__all__ = ("Environment",)


@final
class Environment:
    """Isolated execution environment for running extracted code.

    Provides a stable `env` object where asynchronous initialization can
    place exported data. Use `exec` to run code objects within the
    environment and collect their exports.
    """

    ENV_NAME: ClassVar = "__env__"
    ENTRY: ClassVar = f"_{UUID.replace('-', '_')}"
    ENTRY_TEMPLATE: ClassVar = f"""async def {ENTRY}(): pass
{ENV_NAME}.{ENTRY} = {ENTRY}"""
    __slots__: ClassVar = (
        "__closure",
        "__context",
        "__env",
        "__globals",
        "__locals",
    )

    @classmethod
    def transform_code(cls, ast: Module):
        template = parse(cls.ENTRY_TEMPLATE, "<string>", "exec", type_comments=True)
        if ast.body:
            cast(AsyncFunctionDef, template.body[0]).body = ast.body
        return template

    def __init__(
        self,
        *,
        env: Mapping[str, Any] = {},
        globals: Mapping[str, Any] = globals(),
        locals: Mapping[str, object] = locals(),
        closure: tuple[CellType, ...] | None = None,
        context: Callable[[], AbstractAsyncContextManager[Any]] | None = None,
    ):
        self.__env = MappingProxyType(dict(env))
        self.__globals = MappingProxyType(dict(globals))
        self.__locals = MappingProxyType(dict(locals))
        self.__closure = closure
        self.__context = context if context else lambda: nullcontext()
        assert self.ENV_NAME not in self.globals
        assert self.ENV_NAME not in self.locals

    def __repr__(self):
        return f"{type(self).__qualname__}(env={self.__env!r}, globals={self.__globals!r}, locals={self.__locals!r})"

    def __str__(self):
        def filter(map_: Mapping[str, Any]):
            return {
                key: val
                for key, val in map_.items()
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
    def env(self):
        return self.__env

    @property
    def globals(self):
        return self.__globals

    @property
    def locals(self):
        return self.__locals

    @property
    def closure(self):
        return self.__closure

    async def exec(self, code: CodeType, *init_codes: CodeType) -> Any:
        """Execute `code` and optional `init_codes` in this environment and return any exported result."""
        env = SimpleNamespace(result=None, **self.env)
        globals = {**self.globals, self.ENV_NAME: env}
        locals = (
            globals
            if self.locals == self.globals
            else {**self.locals, self.ENV_NAME: env}
        )
        async with self.__context():
            for init_code in init_codes:
                exec(init_code, globals, locals, closure=self.closure)
                export = await getattr(env, self.ENTRY)()
                if export is not None:
                    globals.update(export)
            exec(code, globals, locals, closure=self.closure)
            return await getattr(env, self.ENTRY)()
