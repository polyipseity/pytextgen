# -*- coding: UTF-8 -*-
import info as _info
import setuptools as _setuptools

_setuptools.setup(
    name=_info.name,
    version=str(_info.version),
    install_requires=("regex",),
)
