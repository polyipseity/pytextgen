# -*- coding: UTF-8 -*-
from . import VERSION as _VER
from .clear.main import __package__ as _clear_package, parser as _clear_parser
from .generate.main import __package__ as _generate_package, parser as _generate_parser
from argparse import ArgumentParser as _ArgParser
from functools import partial as _partial
from sys import modules as _mods
from typing import Callable as _Call


def parser(parent: _Call[..., _ArgParser] | None = None):
    prog0 = _mods[__name__].__package__
    prog = prog0 if prog0 else __name__
    del prog0

    parser = (_ArgParser if parent is None else parent)(
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
    _clear_parser(
        _partial(subparsers.add_parser, _clear_package.replace(f"{prog}.", ""))
    )
    _generate_parser(
        _partial(subparsers.add_parser, _generate_package.replace(f"{prog}.", ""))
    )
    return parser
