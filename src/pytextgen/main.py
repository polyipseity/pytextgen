"""Top-level command line parser for the `pytextgen` package.

This module wires together sub-commands from the `clear` and `generate`
subpackages and exposes a `parser` factory function used by `__main__`.
"""

from argparse import ArgumentParser
from functools import partial
from typing import Callable

from .clear.main import __name__ as clear_name
from .clear.main import __package__ as clear_package
from .clear.main import parser as clear_parser
from .generate.main import __name__ as generate_name
from .generate.main import __package__ as generate_package
from .generate.main import parser as generate_parser
from .meta import VERSION

__all__ = ("parser",)


def parser(parent: Callable[..., ArgumentParser] | None = None):
    """Create the top-level `ArgumentParser` for the CLI.

    Returns a configured `ArgumentParser` with subparsers for the
    `clear` and `generate` subcommands.
    """
    prog = __package__ or __name__

    parser = (ArgumentParser if parent is None else parent)(
        prog=f"python -m {prog}",
        description="tools for notes",
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
    subparsers = parser.add_subparsers(
        required=True,
    )
    clear_parser(
        partial(
            subparsers.add_parser,
            (clear_package or clear_name).replace(f"{prog}.", ""),
        )
    )
    generate_parser(
        partial(
            subparsers.add_parser,
            (generate_package or generate_name).replace(f"{prog}.", ""),
        )
    )
    return parser
