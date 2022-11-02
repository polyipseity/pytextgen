import argparse as _argparse
import contextlib as _contextlib
import dataclasses as _dataclasses
import enum as _enum
import itertools as _itertools
import logging as _logging
import os as _os
import pathlib as _pathlib
import sys as _sys
import typing as _typing

from .. import globals as _globals
from .. import version as _version
from . import *


@_typing.final
@_enum.unique
class ExitCode(_enum.IntFlag):
    READ_ERROR: _typing.ClassVar = _enum.auto()
    VALIDATE_ERROR: _typing.ClassVar = _enum.auto()
    WRITE_ERROR: _typing.ClassVar = _enum.auto()


@_typing.final
@_dataclasses.dataclass(init=True,
                        repr=True,
                        eq=True,
                        order=False,
                        unsafe_hash=False,
                        frozen=True,
                        match_args=True,
                        kw_only=True,
                        slots=True,)
class Arguments:
    inputs: _typing.Sequence[_pathlib.Path]
    options: Options

    def __post_init__(self: _typing.Self) -> None:
        object.__setattr__(self, 'inputs', tuple(
            input.resolve(strict=True) for input in self.inputs))


def main(argv: _typing.Sequence[str]) -> _typing.NoReturn:
    args: Arguments = parse_argv(argv)
    exit_code: ExitCode = ExitCode(0)

    def read(input: _pathlib.Path) -> _typing.Iterable[Writer]:
        nonlocal exit_code
        try:
            file: _typing.TextIO = open(
                input, mode='rt', **_globals.open_options)
        except OSError:
            exit_code |= ExitCode.READ_ERROR
            _logging.exception(f'Cannot open file: {input}')
            return ()
        except ValueError:
            exit_code |= ExitCode.READ_ERROR
            _logging.exception(f'Encoding error opening file: {input}')
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
                _logging.exception(f'Exception reading file: {input}')
                return ()
    writers: _typing.Iterable[Writer] = _itertools.chain.from_iterable(
        map(read, args.inputs))
    writer_stack: _contextlib.ExitStack = _contextlib.ExitStack().__enter__()
    try:
        writer: Writer
        for writer in writers:
            try:
                writer_stack.enter_context(writer.write())
            except Exception:
                exit_code |= ExitCode.VALIDATE_ERROR
                _logging.exception(f'Error while validation: {writer}')
                continue
    finally:
        try:
            writer_stack.close()
        except Exception:
            exit_code |= ExitCode.WRITE_ERROR
            _logging.exception('Error while writing')

    _sys.exit(exit_code)


def parse_argv(argv: _typing.Sequence[str]) -> Arguments | _typing.NoReturn:
    prog0: str | None = _sys.modules[__name__].__package__
    prog: str = prog0 if prog0 else __name__
    del prog0

    parser: _argparse.ArgumentParser = _argparse.ArgumentParser(
        prog=f'python -m {prog}',
        description='generate text from input',
        add_help=True,
        allow_abbrev=False,
        exit_on_error=False,
    )
    parser.add_argument('-v', '--version',
                        action='version',
                        version=f'{prog} v{_version.version}',
                        help='print version and exit',)
    parser.add_argument('-t', '--timestamp',
                        action='store_true',
                        default=True,
                        help='update or write timestamp (default)',
                        dest='timestamp',)
    parser.add_argument('-T', '--no-timestamp',
                        action='store_false',
                        default=False,
                        help='do not update or write timestamp',
                        dest='timestamp',)
    parser.add_argument('--init-flashcards',
                        action='store_true',
                        default=False,
                        help='initialize flashcards',
                        dest='init_flashcards',)
    parser.add_argument('--no-init-flashcards',
                        action='store_false',
                        default=True,
                        help='do not initialize flashcards (default)',
                        dest='init_flashcards',)
    parser.add_argument('inputs',
                        action='store',
                        nargs=_argparse.ONE_OR_MORE,
                        type=lambda path:
                        _pathlib.Path(path).resolve(strict=True),
                        help='sequence of input(s) to read',)
    input: _argparse.Namespace = parser.parse_args(argv[1:])
    return Arguments(
        inputs=input.inputs,
        options=Options(
            timestamp=input.timestamp,
            init_flashcards=input.init_flashcards,
        ),
    )
