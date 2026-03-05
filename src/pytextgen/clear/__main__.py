"""Module entry-point for command-line invocation.

This module is executed when the package is run with `python -m pytextgen
clear`. It configures basic logging and executes the selected CLI
subcommand.
"""

from logging import INFO, basicConfig
from sys import argv

from asyncer import runnify

from .main import parser

"""Public symbols exported by this module."""
__all__ = ("main",)


async def main() -> None:
    """Main entry point for the pytextgen clear CLI.

    Sets up logging, parses arguments, and invokes the selected action.
    """

    basicConfig(level=INFO)
    entry = parser().parse_args(argv[1:])
    await entry.invoke(entry)


def __main__() -> None:
    """Synchronous command-line entrypoint exposed by the package."""

    runnify(main, backend_options={"use_uvloop": True})()


if __name__ == "__main__":
    __main__()
