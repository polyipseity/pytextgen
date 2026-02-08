from . import config as config
from . import gen as gen
from . import read as read
from . import util as util


def dirty() -> bool:
    # Do not use the above imports
    from .config import CONFIG as _CFG
    from .config import Configuration as _Cfg

    return _CFG != _Cfg()
