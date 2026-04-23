"""Tests for :mod:`pytextgen.io.env` (`Environment`)."""

from ast import AsyncFunctionDef, Module, parse
from contextlib import asynccontextmanager
from types import MappingProxyType

import pytest

from pytextgen.io.env import Environment

"""Public symbols exported by this module (none)."""
__all__ = ()


def _compile_transformed(source: str, filename: str = "<test>"):
    """Compile source by passing through ``Environment.transform_code``."""
    module_ast = parse(source, filename=filename, mode="exec", type_comments=True)
    transformed = Environment.transform_code(module_ast)
    return compile(transformed, filename, "exec")


def test_transform_code_wraps_body_in_async_entry() -> None:
    """`transform_code` should place provided body inside async entry function."""
    ast0 = parse("return 42", filename="<ast>", mode="exec", type_comments=True)
    transformed = Environment.transform_code(ast0)

    assert isinstance(transformed, Module)
    assert isinstance(transformed.body[0], AsyncFunctionDef)
    assert transformed.body[0].name == Environment.ENTRY
    assert transformed.body[0].body == ast0.body


@pytest.mark.anyio
async def test_exec_applies_init_code_exports() -> None:
    """Export mappings returned by init codes should be available to main code."""
    env = Environment()

    init_code = _compile_transformed("return {'seed': 5}", filename="<init>")
    main_code = _compile_transformed("return seed + 7", filename="<main>")

    result = await env.exec(main_code, init_code)
    assert result == 12


@pytest.mark.anyio
async def test_exec_runs_context_once() -> None:
    """Custom execution context should be entered and exited for `exec`."""
    seen = {"entered": 0, "exited": 0}

    @asynccontextmanager
    async def context():
        """Track enter/exit counts around execution."""
        seen["entered"] += 1
        try:
            yield
        finally:
            seen["exited"] += 1

    env = Environment(context=lambda: context())
    code = _compile_transformed("return 'ok'", filename="<ctx>")

    assert await env.exec(code) == "ok"
    assert seen == {"entered": 1, "exited": 1}


def test_str_filters_dunder_names_and_repr_includes_class_name() -> None:
    """`str` should hide dunder entries while `repr` keeps diagnostic detail."""
    env = Environment(
        env={"a": 1, "__hidden__": 9},
        globals={"g": 2, "__g__": 0},
        locals={"l": 3, "__l__": 0},
    )

    rendered = str(env)
    debug = repr(env)

    assert "Environment(" in rendered
    assert "Environment(" in debug
    assert "__hidden__" not in rendered
    assert "__g__" not in rendered
    assert "__l__" not in rendered
    assert "a" in rendered and "g" in rendered and "l" in rendered


def test_env_globals_and_locals_are_mapping_proxies() -> None:
    """Environment should expose read-only mapping views."""
    env = Environment(env={"a": 1}, globals={"b": 2}, locals={"c": 3})
    assert isinstance(env.env, MappingProxyType)
    assert isinstance(env.globals, MappingProxyType)
    assert isinstance(env.locals, MappingProxyType)


def test_init_rejects_reserved_env_name_in_globals_or_locals() -> None:
    """Reserved ``ENV_NAME`` key should trigger assertion guards."""
    with pytest.raises(AssertionError):
        Environment(globals={Environment.ENV_NAME: object()})

    with pytest.raises(AssertionError):
        Environment(locals={Environment.ENV_NAME: object()})
