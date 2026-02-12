"""Module entry point used when running `python -m pytextgen`.

This module simply configures logging and dispatches to the top-level
`parser` to invoke subcommands.
"""

from asyncio import run
from logging import INFO, basicConfig
from sys import argv

from .main import parser

__all__ = ()

if __name__ == "__main__":
    basicConfig(level=INFO)
    entry = parser().parse_args(argv[1:])
    run(entry.invoke(entry))
