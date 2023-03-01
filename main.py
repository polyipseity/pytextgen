# -*- coding: UTF-8 -*-
import argparse as _argparse
import functools as _functools
import sys as _sys
import typing as _typing

from . import info as _info


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
        description="tools for notes",
        add_help=True,
        allow_abbrev=False,
        exit_on_error=False,
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"{prog} v{_info.version}",
        help="print version and exit",
    )
    subparsers = parser.add_subparsers()
    from .generate import main as generate_main

    generate_main.parser(
        _functools.partial(
            subparsers.add_parser, generate_main.__package__.replace(f"{prog}.", "")
        )
    )
    from .strip import main as strip_main

    strip_main.parser(
        _functools.partial(
            subparsers.add_parser, strip_main.__package__.replace(f"{prog}.", "")
        )
    )
    return parser
