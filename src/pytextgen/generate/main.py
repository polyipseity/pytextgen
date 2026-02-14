"""CLI 'generate' subcommand: generate content based on input files.

This module exposes an async `main` entry point and a `parser` factory
used by the top-level CLI.
"""

from argparse import ONE_OR_MORE, ArgumentParser, Namespace
from asyncio import gather
from collections.abc import Callable, Iterable, MutableSequence, Sequence
from dataclasses import dataclass
from enum import IntFlag, auto, unique
from functools import partial, reduce, wraps
from itertools import chain
from sys import exit
from typing import final

from anyio import Path

from ..io.options import GenOpts
from ..io.read import Reader
from ..io.write import Writer
from ..meta import LOGGER, VERSION
from ..utils import CompileCache

__all__ = ("ExitCode", "Arguments", "main", "parser")


@final
@unique
class ExitCode(IntFlag):
    """Exit flags used by the `generate` subcommand.

    Signals represent read/validate/write failures and are combinable.
    """

    READ_ERROR = auto()
    VALIDATE_ERROR = auto()
    WRITE_ERROR = auto()


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
    """Parsed arguments container for the `generate` command.

    Attributes:
        inputs: Sequence of input paths to generate from.
        options: Generation options (`GenOpts`) controlling behaviour.
    """

    inputs: Sequence[Path]
    options: GenOpts

    def __post_init__(self):
        """Normalize `inputs` into an immutable tuple after construction."""
        object.__setattr__(self, "inputs", tuple(self.inputs))


async def main(args: Arguments):
    """Main async entry point for the `generate` subcommand.

    Reads inputs, validates and writes generated output. Exits with an
    appropriate `ExitCode` on error.
    """
    exit_code = ExitCode(0)

    async def read(input: Path):
        """Read `input` using `Reader.cached` and return writer sequence or an ExitCode."""
        try:
            return (await Reader.cached(path=input, options=args.options)).pipe()
        except Exception:
            LOGGER.exception(f"Exception reading file: {input}")
            return ExitCode.READ_ERROR

    def reduce_read_result(
        left: tuple[MutableSequence[Iterable[Writer]], ExitCode],
        right: Iterable[Writer] | ExitCode,
    ):
        """Accumulator combining read results into (writers-seq, exit-code)."""
        seq, code = left
        if isinstance(right, ExitCode):
            code |= right
        else:
            seq.append(right)
        return (seq, code)

    writers0, exit_code = reduce(
        reduce_read_result,
        await gather(*map(read, args.inputs)),
        (list[Iterable[Writer]](), exit_code),
    )
    writers = chain.from_iterable(writers0)

    async def write(writer: Writer):
        """Validate and write a single `Writer` instance, returning an ExitCode."""
        write = writer.write()
        try:
            await write.__aenter__()
        except Exception:
            LOGGER.exception(f"Error while validation: {writer}")
            return ExitCode.VALIDATE_ERROR
        try:
            await write.__aexit__(None, None, None)
        except Exception:
            LOGGER.exception(f"Error while writing: {writer}")
            return ExitCode.WRITE_ERROR
        return ExitCode(0)

    exit_code = reduce(
        lambda left, right: left | right,
        await gather(*map(write, writers)),
        exit_code,
    )
    exit(exit_code)


def parser(parent: Callable[..., ArgumentParser] | None = None):
    """Create an `ArgumentParser` for the `generate` subcommand.

    The returned parser is configured with options for timestamping,
    flashcard initialization and code cache options.
    """
    prog = __package__ or __name__

    parser = (ArgumentParser if parent is None else parent)(
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
        version=f"{prog} v{VERSION}",
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
        default=Path("./__pycache__/"),
        type=Path,
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
        nargs=ONE_OR_MORE,
        type=Path,
        help="sequence of input(s) to read",
    )

    @wraps(main)
    async def invoke(args: Namespace):
        """Create a `CompileCache` context and invoke `main` with prepared args."""
        async with CompileCache(
            folder=(
                args.code_cache
                if args.code_cache is None
                else await args.code_cache.resolve()
            )
        ) as cache:
            await main(
                Arguments(
                    inputs=await gather(
                        *map(partial(Path.resolve, strict=True), args.inputs)
                    ),
                    options=GenOpts(
                        timestamp=args.timestamp,
                        init_flashcards=args.init_flashcards,
                        compiler=cache.compile,
                    ),
                )
            )

    parser.set_defaults(invoke=invoke)
    return parser
