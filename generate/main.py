# -*- coding: UTF-8 -*-
import argparse as _argparse
import atexit as _atexit
import contextlib as _contextlib
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import itertools as _itertools
import logging as _logging
import os as _os
import pathlib as _pathlib
import sys as _sys
import typing as _typing

from .. import globals as _globals
from .. import util as _util
from .. import version as _version
from ._read import *
from ._write import *


@_typing.final
@_enum.unique
class ExitCode(_enum.IntFlag):
    READ_ERROR: _typing.ClassVar = _enum.auto()
    VALIDATE_ERROR: _typing.ClassVar = _enum.auto()
    WRITE_ERROR: _typing.ClassVar = _enum.auto()


@_typing.final
@_dataclasses.dataclass(
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
class Arguments:
    inputs: _typing.Sequence[_pathlib.Path]
    options: Options

    def __post_init__(self: _typing.Self) -> None:
        object.__setattr__(
            self, "inputs", tuple(input.resolve(strict=True) for input in self.inputs)
        )


def main(args: Arguments) -> _typing.NoReturn:
    exit_code: ExitCode = ExitCode(0)

    def read(input: _pathlib.Path) -> _typing.Iterable[Writer]:
        nonlocal exit_code
        try:
            file: _typing.TextIO = open(input, mode="rt", **_globals.open_options)
        except OSError:
            exit_code |= ExitCode.READ_ERROR
            _logging.exception(f"Cannot open file: {input}")
            return ()
        except ValueError:
            exit_code |= ExitCode.READ_ERROR
            _logging.exception(f"Encoding error opening file: {input}")
            return ()
        with file:
            try:
                ext: str
                _, ext = _os.path.splitext(input)
                reader: Reader = Reader.registry[ext](
                    path=input,
                    options=args.options,
                )
                reader.read(file.read())
                return reader.pipe()
            except Exception:
                exit_code |= ExitCode.READ_ERROR
                _logging.exception(f"Exception reading file: {input}")
                return ()

    writers: _typing.Iterable[Writer] = _itertools.chain.from_iterable(
        map(read, args.inputs)
    )
    writer_stack: _contextlib.ExitStack = _contextlib.ExitStack().__enter__()
    try:
        writer: Writer
        for writer in writers:
            try:
                writer_stack.enter_context(writer.write())
            except Exception:
                exit_code |= ExitCode.VALIDATE_ERROR
                _logging.exception(f"Error while validation: {writer}")
                continue
    finally:
        try:
            writer_stack.close()
        except Exception:
            exit_code |= ExitCode.WRITE_ERROR
            _logging.exception("Error while writing")

    _sys.exit(exit_code)


def parser(
    parent: _typing.Callable[..., _argparse.ArgumentParser] | None = None,
) -> _argparse.ArgumentParser:
    prog0: str | None = _sys.modules[__name__].__package__
    prog: str = prog0 if prog0 else __name__
    del prog0

    parser: _argparse.ArgumentParser = (
        _argparse.ArgumentParser if parent is None else parent
    )(
        prog=f"python -m {prog}",
        description="generate text from input",
        add_help=True,
        allow_abbrev=False,
        exit_on_error=False,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{prog} v{_version.version}",
        help="print version and exit",
    )
    t_group = parser.add_mutually_exclusive_group()
    t_group.add_argument(
        "-t",
        "--timestamp",
        action="store_true",
        default=True,
        help="update or write timestamp (default)",
        dest="timestamp",
    )
    t_group.add_argument(
        "-T",
        "--no-timestamp",
        action="store_false",
        default=False,
        help="do not update or write timestamp",
        dest="timestamp",
    )
    init_flashcards_group = parser.add_mutually_exclusive_group()
    init_flashcards_group.add_argument(
        "--init-flashcards",
        action="store_true",
        default=False,
        help="initialize flashcards",
        dest="init_flashcards",
    )
    init_flashcards_group.add_argument(
        "--no-init-flashcards",
        action="store_false",
        default=True,
        help="do not initialize flashcards (default)",
        dest="init_flashcards",
    )
    code_cache_group = parser.add_mutually_exclusive_group()
    code_cache_group.add_argument(
        "--code-cache",
        action="store",
        default=_pathlib.Path("./__pycache__/"),
        type=_pathlib.Path,
        help="specify code cache (default: ./__pycache__/)",
        dest="code_cache",
    )
    code_cache_group.add_argument(
        "--no-code-cache",
        action="store_const",
        const=None,
        default=False,
        help="do not use code cache",
        dest="code_cache",
    )
    parser.add_argument(
        "inputs",
        action="store",
        nargs=_argparse.ONE_OR_MORE,
        type=lambda path: _pathlib.Path(path).resolve(strict=True),
        help="sequence of input(s) to read",
    )

    @_functools.wraps(main)
    def invoke(args: _argparse.Namespace) -> _typing.NoReturn:
        if args.code_cache is None:
            compiler: _util.Compiler = compile
        else:
            code_cache: _util.CompileCache = _util.CompileCache(folder=args.code_cache)
            _atexit.register(code_cache.save)
            compiler = code_cache.compile
        main(
            Arguments(
                inputs=args.inputs,
                options=Options(
                    timestamp=args.timestamp,
                    init_flashcards=args.init_flashcards,
                    compiler=compiler,
                ),
            )
        )

    parser.set_defaults(invoke=invoke)
    return parser
