# -*- coding: UTF-8 -*-
from . import config as config, gen as gen, read as read, util as util


def dirty() -> bool:
    return config.CONFIG != config.Configuration()
