"""I/O utilities: readers, writers, and location helpers for pytextgen.

Exports reader and writer classes used by the `generate` and `clear`
subcommands, along with helpers to operate on file sections.
"""

from ._options import ClearOpts, ClearType, GenOpts
from ._read import CodeLibrary, MarkdownReader, Reader
from ._write import ClearWriter, PythonWriter, Writer
from .util import (
    NULL_LOCATION,
    AnyTextIO,
    FileSection,
    Location,
    NullLocation,
    PathLocation,
    Result,
    lock_file,
)

__all__ = (
    "ClearType",
    "ClearOpts",
    "GenOpts",
    "Reader",
    "CodeLibrary",
    "MarkdownReader",
    "Writer",
    "ClearWriter",
    "PythonWriter",
    "AnyTextIO",
    "lock_file",
    "Location",
    "NullLocation",
    "NULL_LOCATION",
    "PathLocation",
    "FileSection",
    "Result",
)
