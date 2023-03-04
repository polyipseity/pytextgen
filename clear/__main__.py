# -*- coding: UTF-8 -*-
import argparse as _argparse
import asyncio as _asyncio
import sys as _sys
from . import main as _main

if __name__ == "__main__":
    entry: _argparse.Namespace = _main.parser().parse_args(_sys.argv[1:])
    _asyncio.run(entry.invoke(entry))