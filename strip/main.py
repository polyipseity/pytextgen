# -*- coding: UTF-8 -*-
import argparse as _argparse
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import logging as _logging
import pathlib as _pathlib
import re as _re
import sys as _sys
import typing as _typing

from .. import globals as _globals
from .. import version as _version
from . import *

_flashcard_states_regex: _re.Pattern[str] = _re.compile(
    r" ?" + _globals.flashcard_states_regex.pattern,
    _globals.flashcard_states_regex.flags,
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
    inputs: _typing.Sequence[_pathlib.Path]

    def __post_init__(self: _typing.Self) -> None:
        object.__setattr__(
            self, "inputs", tuple(input.resolve(strict=True) for input in self.inputs)
        )


def main(args: Arguments) -> _typing.NoReturn:
    exit_code: ExitCode = ExitCode(0)

    input: _pathlib.Path
    for input in args.inputs:
        try:
            file: _typing.TextIO = open(input, mode="r+t", **_globals.open_options)
        except OSError:
            exit_code |= ExitCode.READ_ERROR
            _logging.exception(f"Cannot open file: {input}")
            continue
        except ValueError:
            exit_code |= ExitCode.READ_ERROR
            _logging.exception(f"Encoding error opening file: {input}")
            continue
        with file:
            try:
                text: str = file.read()
            except Exception:
                exit_code |= ExitCode.READ_ERROR
                _logging.exception(f"Exception reading file: {input}")
                continue
            try:
                file.seek(0)
                file.write(_flashcard_states_regex.sub("", text))
                file.truncate()
            except Exception:
                exit_code |= ExitCode.WRITE_ERROR
                _logging.exception(f"Exception writing file: {input}")
                continue

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
    parser.add_argument(
        "inputs",
        action="store",
        nargs=_argparse.ONE_OR_MORE,
        type=lambda path: _pathlib.Path(path).resolve(strict=True),
        help="sequence of input(s) to read",
    )

    @_functools.wraps(main)
    def invoke(args: _argparse.Namespace) -> _typing.NoReturn:
        main(
            Arguments(
                inputs=args.inputs,
            )
        )

    parser.set_defaults(invoke=invoke)
    return parser
