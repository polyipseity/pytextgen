# -*- coding: UTF-8 -*-
from .. import LOGGER as _LOGGER, VERSION as _VER, io as _io, util as _util
import anyio as _anyio
import argparse as _argparse
import asyncio as _asyncio
import dataclasses as _dataclasses
import enum as _enum
import functools as _functools
import itertools as _itertools
import sys as _sys
import typing as _typing


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
    options: _io.GenOpts

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))


async def main(args: Arguments):
    exit_code: ExitCode = ExitCode(0)

    async def read(input: _anyio.Path):
        try:
            return (await _io.Reader.cached(path=input, options=args.options)).pipe()
        except Exception:
            _LOGGER.exception(f"Exception reading file: {input}")
            return ExitCode.READ_ERROR

    def reduce_read_result(
        left: tuple[_typing.MutableSequence[_typing.Iterable[_io.Writer]], ExitCode],
        right: _typing.Iterable[_io.Writer] | ExitCode,
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
        (list[_typing.Iterable[_io.Writer]](), exit_code),
    )
    writers = _itertools.chain.from_iterable(writers0)

    async def write(writer: _io.Writer):
        write = writer.write()
        try:
            await write.__aenter__()
        except Exception:
            _LOGGER.exception(f"Error while validation: {writer}")
            return ExitCode.VALIDATE_ERROR
        try:
            await write.__aexit__(None, None, None)
        except Exception:
            _LOGGER.exception(f"Error while writing: {writer}")
            return ExitCode.WRITE_ERROR
        return ExitCode(0)

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
        version=f"{prog} v{_VER}",
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
            else await args.code_cache.resolve()
        ) as cache:
            await main(
                Arguments(
                    inputs=await _asyncio.gather(
                        *map(
                            _functools.partial(_anyio.Path.resolve, strict=True),
                            args.inputs,
                        )
                    ),
                    options=_io.GenOpts(
                        timestamp=args.timestamp,
                        init_flashcards=args.init_flashcards,
                        compiler=cache.compile,
                    ),
                )
            )

    parser.set_defaults(invoke=invoke)
    return parser
