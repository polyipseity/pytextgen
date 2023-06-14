# -*- coding: UTF-8 -*-
from . import VERSION as _VER
from .clear import main as _clear_main
from .generate import main as _generate_main
import argparse as _argparse
import functools as _functools
import sys as _sys
import typing as _typing


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
        version=f"{prog} v{_VER}",
        help="print version and exit",
    )
    subparsers = parser.add_subparsers(
        required=True,
    )
    _generate_main.parser(
        _functools.partial(
            subparsers.add_parser, _generate_main.__package__.replace(f"{prog}.", "")
        )
    )
    _clear_main.parser(
        _functools.partial(
            subparsers.add_parser, _clear_main.__package__.replace(f"{prog}.", "")
        )
    )
    return parser
