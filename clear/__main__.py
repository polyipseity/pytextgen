# -*- coding: UTF-8 -*-
import asyncio as _asyncio
import sys as _sys
from . import main as _main

if __name__ == "__main__":
    entry = _main.parser().parse_args(_sys.argv[1:])
    _asyncio.run(entry.invoke(entry))
