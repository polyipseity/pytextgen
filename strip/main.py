# -*- coding: UTF-8 -*-
import anyio as _anyio
import argparse as _argparse
import asyncio as _asyncio
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import logging as _logging
import re as _re
import sys as _sys
import typing as _typing

from .. import globals as _globals
from .. import info as _info


_FLASHCARD_STATES_REGEX = _re.compile(
    r" ?" + _globals.FLASHCARD_STATES_REGEX.pattern,
    _globals.FLASHCARD_STATES_REGEX.flags,
)


@_typing.final
@_enum.unique
class ExitCode(_enum.IntFlag):
    READ_ERROR: _typing.ClassVar = _enum.auto()
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

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))


async def main(args: Arguments) -> _typing.NoReturn:
    exit_code = ExitCode(0)

    async def process(input: _anyio.Path):
        try:
            file = await _anyio.open_file(input, mode="r+t", **_globals.OPEN_OPTIONS)
        except OSError:
            _logging.exception(f"Cannot open file: {input}")
            return ExitCode.READ_ERROR
        except ValueError:
            _logging.exception(f"Encoding error opening file: {input}")
            return ExitCode.READ_ERROR
        try:
            try:
                text: str = await file.read()
            except Exception:
                _logging.exception(f"Exception reading file: {input}")
                return ExitCode.READ_ERROR
            try:
                seek = file.seek(0)
                data = _FLASHCARD_STATES_REGEX.sub("", text)
                await seek
                await file.write(data)
                await file.truncate()
            except Exception:
                _logging.exception(f"Exception writing file: {input}")
                return ExitCode.WRITE_ERROR
        finally:
            await file.aclose()
        return 0

    exit_code = _functools.reduce(
        lambda left, right: left | right,
        await _asyncio.gather(*map(process, args.inputs)),
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
                inputs=[await input.resolve(strict=True) for input in args.inputs],
            )
        )

    parser.set_defaults(invoke=invoke)
    return parser
