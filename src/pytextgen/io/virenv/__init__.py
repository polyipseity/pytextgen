from . import config as config
from . import gen as gen
from . import read as read
from . import util as util

__all__ = ("config", "gen", "read", "util", "dirty")


def dirty() -> bool:
    # Use the `config` module imported at package level to avoid re-importing.
    return config.CONFIG != config.Configuration()
