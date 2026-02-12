"""Executable entry point for the `clear` CLI subcommand.

Runs the `parser` and invokes the selected subcommand.
"""

from asyncio import run
from logging import INFO, basicConfig
from sys import argv

from .main import parser

__all__ = ("main",)


def main() -> None:
    """Entry point for the `pytextgen clear` command-line interface."""

    basicConfig(level=INFO)
    entry = parser().parse_args(argv[1:])
    run(entry.invoke(entry))


if __name__ == "__main__":
    main()
