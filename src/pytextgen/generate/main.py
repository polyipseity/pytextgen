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
from itertools import chain as _chain
from sys import exit as _exit
from typing import (
    Callable as _Call,
)
from typing import (
    ClassVar as _ClsVar,
)
from typing import (
    Iterable as _Iter,
)
from typing import (
    MutableSequence as _MSeq,
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
from ..io import GenOpts as _GenOpts
from ..io import Reader as _Reader
from ..io import Writer as _Writer
from ..util import CompileCache as _CompCache


@_fin
@_unq
class ExitCode(_IntFlg):
    READ_ERROR: _ClsVar = _auto()
    VALIDATE_ERROR: _ClsVar = _auto()
    WRITE_ERROR: _ClsVar = _auto()


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
    options: _GenOpts

    def __post_init__(self):
        object.__setattr__(self, "inputs", tuple(self.inputs))


async def main(args: Arguments):
    exit_code = ExitCode(0)

    async def read(input: _Path):
        try:
            return (await _Reader.cached(path=input, options=args.options)).pipe()
        except Exception:
            _LOGGER.exception(f"Exception reading file: {input}")
            return ExitCode.READ_ERROR

    def reduce_read_result(
        left: tuple[_MSeq[_Iter[_Writer]], ExitCode],
        right: _Iter[_Writer] | ExitCode,
    ):
        seq, code = left
        if isinstance(right, ExitCode):
            code |= right
        else:
            seq.append(right)
        return (seq, code)

    writers0, exit_code = _reduce(
        reduce_read_result,
        await _gather(*map(read, args.inputs)),
        (list[_Iter[_Writer]](), exit_code),
    )
    writers = _chain.from_iterable(writers0)

    async def write(writer: _Writer):
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

    exit_code = _reduce(
        lambda left, right: left | right,
        await _gather(*map(write, writers)),
        exit_code,
    )
    _exit(exit_code)


def parser(parent: _Call[..., _ArgParser] | None = None):
    prog = __package__ or __name__

    parser = (_ArgParser if parent is None else parent)(
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
        default=_Path("./__pycache__/"),
        type=_Path,
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
        nargs=_ONE_OR_MORE,
        type=_Path,
        help="sequence of input(s) to read",
    )

    @_wraps(main)
    async def invoke(args: _NS):
        async with _CompCache(
            folder=(
                args.code_cache
                if args.code_cache is None
                else await args.code_cache.resolve()
            )
        ) as cache:
            await main(
                Arguments(
                    inputs=await _gather(
                        *map(_partial(_Path.resolve, strict=True), args.inputs)
                    ),
                    options=_GenOpts(
                        timestamp=args.timestamp,
                        init_flashcards=args.init_flashcards,
                        compiler=cache.compile,
                    ),
                )
            )

    parser.set_defaults(invoke=invoke)
    return parser
