import setuptools as _setuptools
import version as _version

_setuptools.setup(
    name='tools',
    version=str(_version.version),
    install_requires=(
        'regex',
    ),
)
