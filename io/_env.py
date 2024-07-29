from .. import UUID as _UUID
from ast import AsyncFunctionDef as _ASTAFunDef, Module as _ASTMod, parse as _parse
from contextlib import AbstractAsyncContextManager as _AACtxMgr, nullcontext as _nullctx
from types import (
    CellType as _Cell,
    CodeType as _Code,
    MappingProxyType as _FrozenMap,
    SimpleNamespace as _SimpNS,
)
from typing import (
    Any as _Any,
    Callable as _Call,
    ClassVar as _ClsVar,
    Mapping as _Map,
    cast as _cast,
    final as _fin,
)


@_fin
class Environment:
    ENV_NAME: _ClsVar = "__env__"
    ENTRY: _ClsVar = f"_{_UUID.replace('-', '_')}"
    ENTRY_TEMPLATE: _ClsVar = f"""async def {ENTRY}(): pass
{ENV_NAME}.{ENTRY} = {ENTRY}"""
    __slots__: _ClsVar = (
        "__closure",
        "__context",
        "__env",
        "__globals",
        "__locals",
    )

    @classmethod
    def transform_code(cls, ast: _ASTMod):
        template = _parse(cls.ENTRY_TEMPLATE, "<string>", "exec", type_comments=True)
        if ast.body:
            _cast(_ASTAFunDef, template.body[0]).body = ast.body
        return template

    def __init__(
        self,
        *,
        env: _Map[str, _Any] = {},
        globals: _Map[str, _Any] = globals(),
        locals: _Map[str, object] = locals(),
        closure: tuple[_Cell, ...] | None = None,
        context: _Call[[], _AACtxMgr[_Any]] | None = None,
    ):
        self.__env = _FrozenMap(dict(env))
        self.__globals = _FrozenMap(dict(globals))
        self.__locals = _FrozenMap(dict(locals))
        self.__closure = closure
        self.__context = context if context else lambda: _nullctx()
        assert self.ENV_NAME not in self.globals
        assert self.ENV_NAME not in self.locals

    def __repr__(self):
        return f"{type(self).__qualname__}(env={self.__env!r}, globals={self.__globals!r}, locals={self.__locals!r})"

    def __str__(self):
        def filter(map: _Map[str, _Any]):
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

    async def exec(self, code: _Code, *init_codes: _Code):
        env = _SimpNS(result=None, **self.env)
        globals = {**self.globals, self.ENV_NAME: env}
        locals = (
            globals
            if self.locals == self.globals
            else {**self.locals, self.ENV_NAME: env}
        )
        async with self.__context():
            for init_code in init_codes:
                exec(init_code, globals, locals)
                export = await getattr(env, self.ENTRY)()
                if export is not None:
                    globals.update(export)
            exec(code, globals, locals, closure=self.closure)
            return await getattr(env, self.ENTRY)()
