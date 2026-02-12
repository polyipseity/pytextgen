"""CLI 'clear' subcommand: utilities to clear generated content from files.

Provide an async `main` entry point and a `parser` factory wired into the
top-level CLI.
"""

from argparse import ONE_OR_MORE, ArgumentParser, Namespace
from asyncio import gather
from dataclasses import dataclass
from enum import IntFlag, auto, unique
from functools import partial, reduce, wraps
from sys import exit
from typing import AbstractSet, Callable, Sequence, final

from anyio import Path

from ..io.options import ClearOpts, ClearType
from ..io.write import ClearWriter
from ..meta import LOGGER, VERSION

__all__ = ("ExitCode", "Arguments", "main", "parser")


@final
@unique
class ExitCode(IntFlag):
    """Exit flags used by the `clear` subcommand.

    Values are combinable using bitwise-or to signal multiple error
    conditions to the process exit code.
    """

    ERROR = auto()


@final
@dataclass(
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

    inputs: Sequence[Path]
    types: AbstractSet[ClearType]

    def __post_init__(self):
        """Normalize container attributes after dataclass initialization.

        Ensures `inputs` is a tuple and `types` is a frozenset for stable
        downstream usage and hashing.
        """
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "types", frozenset(self.types))


async def main(args: Arguments):
    """Main async entry point for the `clear` command.

    Processes inputs according to `args` and writes cleared files back to
    disk. Returns by calling `sys.exit` with an `ExitCode` value.
    """
    exit_code = ExitCode(0)
    options = ClearOpts(types=args.types)

    async def write(input: Path):
        try:
            async with ClearWriter(input, options=options).write():
                pass
        except Exception:
            LOGGER.exception(f"Exception writing file: {input}")
            return ExitCode.ERROR
        return ExitCode(0)

    exit_code = reduce(
        lambda left, right: left | right,
        await gather(*map(write, args.inputs)),
        exit_code,
    )
    exit(exit_code)


def parser(parent: Callable[..., ArgumentParser] | None = None):
    """Create an `ArgumentParser` for the `clear` subcommand.

    The returned parser is configured to parse `inputs` and the `--type`
    option used to tell the command what to clear.
    """
    prog = __package__ or __name__

    parser = (ArgumentParser if parent is None else parent)(
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
        version=f"{prog} v{VERSION}",
        help="print version and exit",
    )
    parser.add_argument(
        "-t",
        "--type",
        action="store",
        nargs=ONE_OR_MORE,
        choices=ClearType.__members__.values(),
        type=ClearType,
        default=frozenset({ClearType.CONTENT}),
        dest="types",
        help="list of type(s) of data to clear",
    )
    parser.add_argument(
        "inputs",
        action="store",
        nargs=ONE_OR_MORE,
        type=Path,
        help="sequence of input(s) to read",
    )

    @wraps(main)
    async def invoke(args: Namespace):
        await main(
            Arguments(
                inputs=await gather(
                    *map(
                        partial(Path.resolve, strict=True),
                        args.inputs,
                    )
                ),
                types=args.types,
            )
        )

    parser.set_defaults(invoke=invoke)
    return parser
