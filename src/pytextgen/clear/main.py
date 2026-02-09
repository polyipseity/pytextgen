"""CLI 'clear' subcommand: utilities to clear generated content from files.

Provide an async `main` entry point and a `parser` factory wired into the
top-level CLI.
"""

from argparse import (
    ONE_OR_MORE as _ONE_OR_MORE,
)
from argparse import (
    ArgumentParser as _ArgParser,
)
from argparse import (
    Namespace as _NS,
)
from asyncio import gather as _gather
from dataclasses import dataclass as _dc
from enum import IntFlag as _IntFlg
from enum import auto as _auto
from enum import unique as _unq
from functools import partial as _partial
from functools import reduce as _reduce
from functools import wraps as _wraps
from sys import exit as _exit
from typing import (
    AbstractSet as _ASet,
)
from typing import (
    Callable as _Call,
)
from typing import (
    Sequence as _Seq,
)
from typing import (
    final as _fin,
)

from anyio import Path as _Path

from .. import LOGGER as _LOGGER
from .. import VERSION as _VER
from ..io import ClearOpts as _ClrOpts
from ..io import ClearType as _ClrT
from ..io import ClearWriter as _ClrWriter

__all__ = ("ExitCode", "Arguments", "main", "parser")


@_fin
@_unq
class ExitCode(_IntFlg):
    """Exit flags used by the `clear` subcommand.

    Values are combinable using bitwise-or to signal multiple error
    conditions to the process exit code.
    """

    ERROR = _auto()


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
    """Container for parsed command-line arguments for `clear`.

    Attributes:
        inputs: Sequence of input paths to process.
        types: Set of `ClearType` values indicating what to clear.
    """

    inputs: _Seq[_Path]
    types: _ASet[_ClrT]

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "types", frozenset(self.types))


async def main(args: Arguments):
    """Main async entry point for the `clear` command.

    Processes inputs according to `args` and writes cleared files back to
    disk. Returns by calling `sys.exit` with an `ExitCode` value.
    """
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
    """Create an `ArgumentParser` for the `clear` subcommand.

    The returned parser is configured to parse `inputs` and the `--type`
    option used to tell the command what to clear.
    """
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
