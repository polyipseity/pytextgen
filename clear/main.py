# -*- coding: UTF-8 -*-
import anyio as _anyio
import argparse as _argparse
import asyncio as _asyncio
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import logging as _logging
import sys as _sys
import typing as _typing

from .. import info as _info
from ..io import ClearOpts as _ClrOpts, ClearType as _ClrT, ClearWriter as _ClrWriter


@_typing.final
@_enum.unique
class ExitCode(_enum.IntFlag):
    ERROR: _typing.ClassVar = _enum.auto()


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
    types: _typing.AbstractSet[_ClrT]

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "types", frozenset(self.types))


async def main(args: Arguments) -> _typing.NoReturn:
    exit_code = ExitCode(0)
    options = _ClrOpts(types=args.types)

    async def write(input: _anyio.Path):
        try:
            async with _ClrWriter(input, options=options).write():
                pass
        except Exception:
            _logging.exception(f"Exception writing file: {input}")
            return ExitCode.ERROR
        return 0

    exit_code = _functools.reduce(
        lambda left, right: left | right,
        await _asyncio.gather(*map(write, args.inputs)),
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
        description="clear generated text in input",
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
    parser.add_argument(
        "-t",
        "--type",
        action="store",
        nargs=_argparse.ONE_OR_MORE,
        choices=_ClrT.__members__.values(),
        type=_ClrT,
        default=frozenset({_ClrT.CONTENT}),
        dest="types",
        help="list of type(s) of data to clear",
    )
    parser.add_argument(
        "inputs",
        action="store",
        nargs=_argparse.ONE_OR_MORE,
        type=_anyio.Path,
        help="sequence of input(s) to read",
    )

    @_functools.wraps(main)
    async def invoke(args: _argparse.Namespace) -> _typing.NoReturn:
        await main(
            Arguments(
                inputs=await _asyncio.gather(
                    *map(
                        _functools.partial(_anyio.Path.resolve, strict=True),
                        args.inputs,
                    )
                ),
                types=args.types,
            )
        )

    parser.set_defaults(invoke=invoke)
    return parser
