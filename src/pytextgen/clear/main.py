from .. import LOGGER as _LOGGER, VERSION as _VER
from ..io import ClearOpts as _ClrOpts, ClearType as _ClrT, ClearWriter as _ClrWriter
from anyio import Path as _Path
from argparse import (
    ArgumentParser as _ArgParser,
    Namespace as _NS,
    ONE_OR_MORE as _ONE_OR_MORE,
)
from asyncio import gather as _gather
from dataclasses import dataclass as _dc
from enum import IntFlag as _IntFlg, auto as _auto, unique as _unq
from functools import partial as _partial, reduce as _reduce, wraps as _wraps
from sys import exit as _exit
from typing import (
    AbstractSet as _ASet,
    Callable as _Call,
    ClassVar as _ClsVar,
    Sequence as _Seq,
    final as _fin,
)


@_fin
@_unq
class ExitCode(_IntFlg):
    ERROR: _ClsVar = _auto()


@_fin
@_dc(
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
    inputs: _Seq[_Path]
    types: _ASet[_ClrT]

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "types", frozenset(self.types))


async def main(args: Arguments):
    exit_code = ExitCode(0)
    options = _ClrOpts(types=args.types)

    async def write(input: _Path):
        try:
            async with _ClrWriter(input, options=options).write():
                pass
        except Exception:
            _LOGGER.exception(f"Exception writing file: {input}")
            return ExitCode.ERROR
        return ExitCode(0)

    exit_code = _reduce(
        lambda left, right: left | right,
        await _gather(*map(write, args.inputs)),
        exit_code,
    )
    _exit(exit_code)


def parser(parent: _Call[..., _ArgParser] | None = None):
    prog = __package__ or __name__

    parser = (_ArgParser if parent is None else parent)(
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
        version=f"{prog} v{_VER}",
        help="print version and exit",
    )
    parser.add_argument(
        "-t",
        "--type",
        action="store",
        nargs=_ONE_OR_MORE,
        choices=_ClrT.__members__.values(),
        type=_ClrT,
        default=frozenset({_ClrT.CONTENT}),
        dest="types",
        help="list of type(s) of data to clear",
    )
    parser.add_argument(
        "inputs",
        action="store",
        nargs=_ONE_OR_MORE,
        type=_Path,
        help="sequence of input(s) to read",
    )

    @_wraps(main)
    async def invoke(args: _NS):
        await main(
            Arguments(
                inputs=await _gather(
                    *map(
                        _partial(_Path.resolve, strict=True),
                        args.inputs,
                    )
                ),
                types=args.types,
            )
        )

    parser.set_defaults(invoke=invoke)
    return parser
