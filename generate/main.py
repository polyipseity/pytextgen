# -*- coding: UTF-8 -*-
import aiofiles as _aiofiles
import anyio as _anyio
import argparse as _argparse
import asyncio as _asyncio
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import itertools as _itertools
import logging as _logging
import os as _os
import sys as _sys
import typing as _typing

from .. import globals as _globals
from .. import info as _info
from .. import util as _util
from ._options import Options
from ._read import Reader
from ._write import Writer


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
    inputs: _typing.Sequence[_anyio.Path]
    options: Options

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))


async def main(args: Arguments):
    exit_code: ExitCode = ExitCode(0)

    async def read(input: _anyio.Path):
        try:
            file = await _aiofiles.open(input, mode="rt", **_globals.OPEN_OPTIONS)
        except OSError:
            _logging.exception(f"Cannot open file: {input}")
            return ExitCode.READ_ERROR
        except ValueError:
            _logging.exception(f"Encoding error opening file: {input}")
            return ExitCode.READ_ERROR
        try:
            try:
                ext: str
                _, ext = _os.path.splitext(input)
                reader: Reader = Reader.registry[ext](
                    path=input,
                    options=args.options,
                )
                reader.read(await file.read())
                return reader.pipe()
            except Exception:
                _logging.exception(f"Exception reading file: {input}")
                return ExitCode.READ_ERROR
        finally:
            await file.close()

    def reduce_read_result(
        left: tuple[_typing.MutableSequence[_typing.Iterable[Writer]], ExitCode],
        right: _typing.Iterable[Writer] | ExitCode,
    ):
        seq, code = left
        if isinstance(right, ExitCode):
            code |= right
        else:
            seq.append(right)
        return (seq, code)

    writers0, exit_code = _functools.reduce(
        reduce_read_result,
        await _asyncio.gather(*map(read, args.inputs)),
        (list[_typing.Iterable[Writer]](), exit_code),
    )
    writers = _itertools.chain.from_iterable(writers0)

    async def write(writer: Writer):
        write = writer.write()
        try:
            await write.__aenter__()
        except Exception:
            _logging.exception(f"Error while validation: {writer}")
            return ExitCode.VALIDATE_ERROR
        try:
            await write.__aexit__(None, None, None)
        except Exception:
            _logging.exception(f"Error while writing: {writer}")
            return ExitCode.WRITE_ERROR
        return 0

    exit_code = _functools.reduce(
        lambda left, right: left | right,
        await _asyncio.gather(*map(write, writers)),
        exit_code,
    )
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
        version=f"{prog} v{_info.VERSION}",
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
        default=_anyio.Path("./__pycache__/"),
        type=_anyio.Path,
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
        type=_anyio.Path,
        help="sequence of input(s) to read",
    )

    @_functools.wraps(main)
    async def invoke(args: _argparse.Namespace):
        async with _util.CompileCache(
            folder=args.code_cache
            if args.code_cache is None
            else await args.code_cache.resolve(strict=True)
        ) as cache:
            await main(
                Arguments(
                    inputs=[await input.resolve(strict=True) for input in args.inputs],
                    options=Options(
                        timestamp=args.timestamp,
                        init_flashcards=args.init_flashcards,
                        compiler=cache.compile,
                    ),
                )
            )

    parser.set_defaults(invoke=invoke)
    return parser
