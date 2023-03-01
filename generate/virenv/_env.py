# -*- coding: UTF-8 -*-
import contextlib as _contextlib
import types as _types
import typing as _typing


@_typing.final
class Environment:
    __slots__: _typing.ClassVar = (
        "__closure",
        "__context",
        "__env",
        "__globals",
        "__locals",
    )

    def __init__(
        self,
        *,
        env: _typing.Mapping[str, _typing.Any | None] = {},
        globals: _typing.Mapping[str, _typing.Any | None] = globals(),
        locals: _typing.Mapping[str, _typing.Any | None] = locals(),
        closure: tuple[_types.CellType, ...] | None = None,
        context: _typing.Callable[[], _contextlib.AbstractContextManager[_typing.Any]]
        | None = None,
    ) -> None:
        self.__env: _typing.Mapping[str, _typing.Any | None] = _types.MappingProxyType(
            dict(env)
        )
        self.__globals: _typing.Mapping[
            str, _typing.Any | None
        ] = _types.MappingProxyType(dict(globals))
        self.__locals: _typing.Mapping[
            str, _typing.Any | None
        ] = _types.MappingProxyType(dict(locals))
        self.__closure = closure
        if context is None:

            @_contextlib.contextmanager
            def dummy_context():
                yield

            self.__context = dummy_context
        else:
            self.__context = context
        assert "__env__" not in self.__globals
        assert "__env__" not in self.__locals

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(env={self.__env!r}, globals={self.__globals!r}, locals={self.__locals!r})"

    def __str__(self) -> str:
        def filter(map: _typing.Mapping[str, _typing.Any | None]):
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
    def env(self) -> _typing.Mapping[str, _typing.Any | None]:
        return self.__env

    @property
    def globals(self) -> _typing.Mapping[str, _typing.Any | None]:
        return self.__globals

    @property
    def locals(self) -> _typing.Mapping[str, _typing.Any | None]:
        return self.__locals

    def exec(self, code: _types.CodeType) -> _typing.Any | None:
        env = _types.SimpleNamespace(result=None, **self.__env)
        globals = {**self.__globals, "__env__": env}
        locals = (
            globals
            if self.__locals == self.__globals
            else {**self.__locals, "__env__": env}
        )
        with self.__context():
            exec(code, globals, locals, closure=self.__closure)
        return env.result
