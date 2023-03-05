# -*- coding: UTF-8 -*-
from . import config as config, gen as gen, read as read, util as util


def dirty() -> bool:
    # Do not use the above imports
    from . import config as _config

    return _config.CONFIG != _config.Configuration()
