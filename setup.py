# -*- coding: UTF-8 -*-
import setuptools as _setuptools
import version as _version

_setuptools.setup(
    name="notes-tools",
    version=str(_version.version),
    install_requires=("regex",),
)
