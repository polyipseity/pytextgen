# -*- coding: UTF-8 -*-
import setuptools as _setuptools
import version as _version

_setuptools.setup(
    name="pytextgen",
    version=str(_version.version),
    install_requires=("regex",),
)
