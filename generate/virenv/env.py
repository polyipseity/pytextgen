import types as _types
import typing as _typing


@_typing.final
class Environment:
    __slots__: _typing.ClassVar = ('__env', '__globals', '__locals')

    def __init__(self: _typing.Self, *,
                 env: _typing.Mapping[str, _typing.Any | None] = {},
                 globals: _typing.Mapping[str, _typing.Any | None] = globals(),
                 locals: _typing.Mapping[str, _typing.Any | None] = locals()) -> None:
        self.__env: _typing.Mapping[str, _typing.Any | None] = _types.MappingProxyType(
            dict(env))
        self.__globals: _typing.Mapping[str, _typing.Any | None] = _types.MappingProxyType(
            dict(globals))
        self.__locals: _typing.Mapping[str, _typing.Any | None] = _types.MappingProxyType(
            dict(locals))
        assert '__env__' not in self.__locals

    def __repr__(self: _typing.Self) -> str:
        return f'{Environment.__qualname__}(env={self.__env!r}, globals={self.__globals!r}, locals={self.__locals!r})'

    @property
    def env(self: _typing.Self) -> _typing.Mapping[str, _typing.Any | None]:
        return self.__env

    @property
    def globals(self: _typing.Self) -> _typing.Mapping[str, _typing.Any | None]:
        return self.__globals

    @property
    def locals(self: _typing.Self) -> _typing.Mapping[str, _typing.Any | None]:
        return self.__locals

    def exec(self: _typing.Self, code: _types.CodeType) -> _typing.Any | None:
        env: _types.SimpleNamespace = _types.SimpleNamespace(
            result=None, **self.__env)
        locals: _types.SimpleNamespace = _types.SimpleNamespace(
            __env__=env, **self.__locals)
        exec(code, dict(self.__globals), locals.__dict__)
        return env.result
