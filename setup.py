# -*- coding: UTF-8 -*-
import info as _info
from setuptools import setup

setup(
    author="polyipseity",
    author_email="polyipseity@gmail.com",
    include_package_data=True,
    install_requires=[
        "anyio",
        "regex",
    ],
    license="AGPL-3.0-or-later",
    name=_info.NAME,
    packages=[_info.NAME],
    python_requires=">=3.11.0",
    version=str(_info.VERSION),
)
