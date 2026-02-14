"""Consolidated tests for `pytextgen.utils` and related helpers.

This file is the merged destination for previous `test_utils_*` and
`test_property_*` modules. Tests are grouped by feature and imports
are deduplicated.
"""

from __future__ import annotations

import ast
import json
import string
import sys
import tempfile
from abc import ABCMeta
from collections.abc import Iterator
from os import PathLike
from threading import Lock
from types import ModuleType
from typing import Any, Literal, cast

import pytest
from anyio import Path, TemporaryDirectory
from hypothesis import given
from hypothesis import strategies as st

from pytextgen.io.env import Environment
from pytextgen.io.options import GenOpts
from pytextgen.io.read import Reader
from pytextgen.io.utils import Location, PathLocation, Result
from pytextgen.io.write import PythonWriter
from pytextgen.utils import (
    CompileCache,
    IteratorSequence,
    TypedTuple,
    Unit,
    abc_subclasshook_check,
    affix_lines,
    async_lock,
    constant,
    deep_copy_package,
    identity,
    ignore_args,
    split_by_punctuations,
    strip_lines,
    tuple1,
)

__all__ = ()


# ----- small/unit tests -----------------------------------------------------


@pytest.mark.asyncio
async def test_CompileCache_metadata_roundtrip(tmp_path: PathLike[str]):
    """Compiled cache persists metadata and can be read back."""
    folder = Path(tmp_path) / "cache"
    async with CompileCache(folder=folder) as cache:
        code = cache.compile("a=1\n", filename="test", mode="exec")
        assert hasattr(code, "co_code")

    md = folder / "metadata.json"
    assert await md.exists()
    data = json.loads(await md.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    data: list[Any] = data  # For type checking
    assert len(data) >= 1
    entry = data[0]
    assert "key" in entry and "value" in entry
    key = entry["key"]
    assert "source" in key and "filename" in key


@pytest.mark.asyncio
async def test_CompileCache_inmemory_and_disk(tmp_path: PathLike[str]):
    """CompileCache operates in-memory and when backed by a folder."""
    # in-memory cache (folder=None)
    async with CompileCache(folder=None) as cache:
        code = cache.compile("a=1", filename="test", mode="exec")
        assert hasattr(code, "co_code")

    # disk-backed cache persists metadata
    folder = Path(tmp_path) / "cc"
    async with CompileCache(folder=folder) as cache:
        code1 = cache.compile("b=2", filename="test2", mode="exec")
        assert hasattr(code1, "co_code")
        repr_str = repr(cache)
        assert "CompileCache" in repr_str

    md = folder / "metadata.json"
    assert await md.exists()
    data = await md.read_text(encoding="utf-8")
    assert "cache_name" in data or "filename" in data


@pytest.mark.asyncio
async def test_CompileCache_handles_ast_and_expression(tmp_path: PathLike[str]):
    """CompileCache accepts AST and expression inputs for compilation."""
    folder = Path(tmp_path) / "cc2"
    async with CompileCache(folder=folder) as cache:
        # compile from source string
        c1 = cache.compile("x=1", filename="f", mode="exec")
        # compile from AST module
        mod = ast.parse("y=2", filename="f", mode="exec")
        c2 = cache.compile(mod, filename="f", mode="exec")
        assert c1 is not None and c2 is not None

    md = folder / "metadata.json"
    assert await md.exists()
    data = await md.read_text(encoding="utf-8")
    assert "cache_name" in data or "filename" in data


def test_identity_constant_ignore_tuple1():
    """Small helper functions behave as identity/constant/ignore_args/tuple1."""
    assert identity(7) == 7
    f = constant(10)
    assert f() == 10 and f(1, 2) == 10
    g = ignore_args(lambda: "ok")
    # ignore_args accepts extra positional args but not keyword arguments
    assert g(1, 2) == "ok"
    assert tuple1(5) == (5,)


@pytest.mark.asyncio
async def test_async_lock_releases():
    """async_lock acquires and releases a threading Lock in async contexts."""
    lock = Lock()
    async with async_lock(lock):
        assert lock.locked()
    assert not lock.locked()


def test_Unit_and_TypedTuple_and_IteratorSequence():
    """Unit, TypedTuple and IteratorSequence utility behaviours are correct."""
    u = Unit(3)
    assert u.counit() == 3
    assert u.map(lambda x: x + 1).counit() == 4

    def dbl(x: int) -> Unit[int]:
        """Small helper used with ``Unit.bind`` in unit tests (double the value)."""
        return Unit(x * 2)

    assert u.bind(dbl).counit() == 6
    assert u.duplicate().join().counit() == 3

    class Ints(TypedTuple[int], element_type=int):
        """TypedTuple specialization used in tests to exercise TypedTuple behaviour."""

        pass

    t = Ints([1, 2, 3])
    assert isinstance(t, tuple) and "Ints" in repr(t)

    it: Iterator[int] = iter(range(5))
    seq = IteratorSequence(it)
    assert seq[0] == 0
    assert len(seq) == 5
    with pytest.raises(IndexError):
        _ = seq[10]
    # slicing returns same type
    s2 = seq[1:3]
    assert isinstance(s2, IteratorSequence)


def test_IteratorSequence_slices():
    """IteratorSequence supports slicing and indexing as a sequence view."""
    seq = IteratorSequence(iter(range(5)))
    s2 = seq[slice(1, 4)]
    assert list(s2) == [1, 2, 3]


def test_deep_copy_package_basic_and_string_accepts():
    """deep_copy_package returns fresh module objects for modules/packages."""
    # plain module -> single (name, module) tuple returned
    mod = __import__("pytextgen.utils", fromlist=["*"])
    results = list(deep_copy_package(mod))
    assert len(results) == 1
    name, new_mod = results[0]
    assert name == mod.__name__
    assert isinstance(new_mod, ModuleType)
    # fresh import should produce a different object than the cached module
    assert sys.modules.get(name) is not new_mod

    # accept module-name string as input
    results2 = list(deep_copy_package(mod.__name__))
    assert results2[0][0] == name


def test_deep_copy_package_discovers_virenv_submodules():
    """deep_copy_package discovers submodules for package imports."""
    mod = __import__("pytextgen.io.virenv", fromlist=["*"])

    # discover on-disk submodules directly (do not use removed helper)
    spec = getattr(mod, "__spec__", None)
    assert spec is not None and spec.submodule_search_locations is not None
    expected = {mod.__name__}
    for _finder, nm, _ispkg in __import__("pkgutil").walk_packages(
        path=spec.submodule_search_locations, prefix=mod.__name__ + "."
    ):
        expected.add(nm)

    pairs = list(deep_copy_package(mod))
    returned_names = {n for n, _ in pairs}

    # ensure all discovered on-disk names are present in the fresh import
    assert expected <= returned_names

    # root package should be yielded first and tuples are (name, ModuleType)
    assert pairs[0][0] == mod.__name__
    for name, ret_mod in pairs:
        assert isinstance(name, str)
        assert isinstance(ret_mod, ModuleType)
        assert ret_mod.__name__ == name
        # must be fresh (different object than sys.modules entry)
        assert sys.modules.get(name) is not ret_mod

    # string input yields the same set of names
    pairs_from_str = list(deep_copy_package(mod.__name__))
    assert {n for n, _ in pairs_from_str} == returned_names


def test_abc_subclasshook_check_structural_and_errors():
    """abc_subclasshook_check raises and returns expected sentinel values."""
    with pytest.raises(ValueError):
        abc_subclasshook_check(
            cast(ABCMeta, object.__class__),
            cast(ABCMeta, object.__class__),
            object,
            names=("x",),
            typing=cast(Literal["nominal"], "bad"),  # intentional cast to trigger error
        )

    assert (
        abc_subclasshook_check(
            cast(ABCMeta, object.__class__),
            cast(ABCMeta, type),
            int,
            names=("__init__",),
        )
        is NotImplemented
    )


def test_abc_subclasshook_check_structural_for_Reader():
    """Structural `__subclasshook__` checks for `Reader` behave as expected."""

    class S:
        """Structural test helper exposing ``options``/``path``/``read``/``pipe``."""

        options = None

        path = None

        async def read(self, text: str):
            """Async placeholder used to satisfy structural checks."""
            pass

        def pipe(self):
            """Return an empty sequence for the structural Reader check."""
            return ()

    assert (
        abc_subclasshook_check(
            Reader,
            Reader,
            S,
            names=("options", "path", "read", "pipe"),
            typing="structural",
        )
        is not True
    )


def test_affix_strip_and_split():
    """affix_lines, strip_lines and split_by_punctuations provide expected outputs."""
    txt = "one\ntwo"
    assert affix_lines(txt, prefix="<", suffix=">") == "<one>\n<two>"
    assert strip_lines(" a \n b \n") == "a\nb"
    parts = list(split_by_punctuations("hello,world;test"))
    assert any("hello" in p for p in parts)


# ----- property / Hypothesis tests -----------------------------------------


@given(
    lines=st.lists(st.text(min_size=0, max_size=20), min_size=0, max_size=10),
    prefix=st.text(max_size=5),
    suffix=st.text(max_size=5),
)
def test_affix_lines_property(lines: list[str], prefix: str, suffix: str):
    """Property-based test: `affix_lines` round-trips correctly for many inputs."""
    text = "\n".join(lines)
    out = affix_lines(text, prefix=prefix, suffix=suffix)
    split_lines = text.splitlines()
    expected = "\n".join(f"{prefix}{line}{suffix}" for line in split_lines)
    assert out == expected


@given(text=st.text())
def test_strip_lines_property_matches_line_strip(text: str):
    """strip_lines behaves like invoking str.strip on each line."""
    joined = strip_lines(text)
    expected = "\n".join(line.strip(None) for line in text.splitlines())
    assert joined == expected


@given(
    s=st.text(
        alphabet=(string.ascii_letters + string.digits + string.punctuation),
        min_size=0,
        max_size=200,
    )
)
def test_split_by_punctuations_returns_nonpunct_parts(s: str):
    """split_by_punctuations divides input into parts with punctuation boundaries."""
    parts = list(split_by_punctuations(s))
    orig_no_punct = "".join(c for c in s if c not in string.punctuation)
    parts_no_punct = "".join(
        "".join(c for c in p if c not in string.punctuation) for p in parts
    )
    assert orig_no_punct == parts_no_punct


@given(
    lst=st.lists(st.integers(min_value=-1000, max_value=1000), min_size=0, max_size=50)
)
def test_iteratorsequence_property(lst: list[int]):
    """IteratorSequence yields values consistent with the original iterator."""
    seq = IteratorSequence(iter(lst))
    assert list(seq) == lst
    if len(lst) > 0:
        i = len(lst) // 2
        assert seq[i] == lst[i]


@pytest.mark.asyncio
@given(n=st.integers(min_value=-1000, max_value=1000))
async def test_compilecache_cache_hits_property(n: int):
    """CompileCache returns same code object for repeated compilation with same key."""
    folder = None
    async with CompileCache(folder=folder) as cache:
        src = f"x={n}"
        code1 = cache.compile(src, filename="hp", mode="exec")
        code2 = cache.compile(src, filename="hp", mode="exec")
        assert code1.co_code == code2.co_code

    with tempfile.TemporaryDirectory() as td:
        folder = Path(td) / "cch"
        async with CompileCache(folder=folder) as cache2:
            _ = cache2.compile(src, filename="hp", mode="exec")
        assert await (folder / "metadata.json").exists()


# ----- integration / env-writer tests -------------------------------------


@given(
    values=st.lists(st.text(min_size=0, max_size=40), min_size=1, max_size=5),
    timestamp=st.booleans(),
)
@pytest.mark.asyncio
async def test_PythonWriter_writes_generated_results(
    values: list[str], timestamp: bool
):
    """PythonWriter writes Results returned from executed code, optionally with a timestamp."""
    async with TemporaryDirectory() as td:
        out_path = Path(td) / "out.txt"
        await out_path.write_text("", encoding="utf-8")

        def make_result(text: str):
            """Factory used in the test to build ``Result`` objects for the writer."""
            return Result(
                location=cast(Location, PathLocation(path=out_path)), text=text
            )

        env = Environment(globals={"make_result": make_result})

        def _mk_source_returning_results(values: list[str]) -> str:
            """Return source text that, when executed, returns the requested Results."""
            if len(values) == 1:
                return f"return make_result({values[0]!r})"
            return "return [" + ",".join(f"make_result({v!r})" for v in values) + "]"

        src = _mk_source_returning_results(values)
        module_ast = ast.parse(src, filename="<hyp>", mode="exec", type_comments=True)
        code_obj = Environment.transform_code(module_ast)
        code = compile(code_obj, "<hyp>", "exec")

        writer = PythonWriter(
            code,
            init_codes=(),
            env=env,
            options=GenOpts(
                timestamp=timestamp, init_flashcards=False, compiler=compile
            ),
        )

        async with writer.write():
            pass

        txt = await out_path.read_text(encoding="utf-8")

        def norm(s: str) -> str:
            """Normalise line endings to LF for comparison in assertions."""
            return s.replace("\r\n", "\n").replace("\r", "\n")

        for v in values:
            assert norm(v) in norm(txt)

        if timestamp and any(v != "" for v in values):
            assert txt.startswith("<!-- The following content is generated")
