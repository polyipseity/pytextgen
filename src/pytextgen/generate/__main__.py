from asyncio import run as _run
from logging import INFO, basicConfig
from sys import argv as _argv

from .main import parser as _parser

if __name__ == "__main__":
    basicConfig(level=INFO)
    entry = _parser().parse_args(_argv[1:])
    _run(entry.invoke(entry))
