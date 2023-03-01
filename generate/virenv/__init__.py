# -*- coding: UTF-8 -*-
from ._env import *
from . import config as config
from . import gen as gen
from . import read as read
from . import util as util


def dirty() -> bool:
    return config.CONFIG != config.Configuration()
