from . import config as config, gen as gen, read as read, util as util


def dirty() -> bool:
    # Do not use the above imports
    from .config import CONFIG as _CFG, Configuration as _Cfg

    return _CFG != _Cfg()
