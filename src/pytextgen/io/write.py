"""Writer abstractions and concrete writers.

Defines the `Writer` protocol and implementations that either clear
sections (`ClearWriter`) or write generated Python-based output
(`PythonWriter`).
"""

import re
from abc import ABCMeta, abstractmethod
from asyncio import gather
from collections.abc import AsyncIterator, Iterable, MutableSequence, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager, nullcontext
from datetime import datetime
from types import CodeType
from typing import Any, ClassVar, cast

from anyio import Path

from ..meta import (
    FLASHCARD_STATES_REGEX,
    GENERATE_COMMENT_FORMAT,
    GENERATE_COMMENT_REGEX,
)
from ..utils import abc_subclasshook_check
from .env import Environment
from .options import ClearOpts, ClearType, GenOpts
from .utils import AnyTextIO, FileSection, Location, Result, lock_file, wrap_async

__all__ = ("Writer", "ClearWriter", "PythonWriter")


class Writer(metaclass=ABCMeta):
    """Abstract writer protocol for writing or clearing content.

    Implementations should expose a `write` async context manager.
    """

    __slots__: ClassVar = ()

    @abstractmethod
    def write(self) -> AbstractAsyncContextManager[None]:
        """Return an async context manager performing the writer action."""
        raise NotImplementedError(self)

    @classmethod
    def __subclasshook__(cls, subclass: type):
        """Structural check used by `issubclass` to recognise Writer-like types."""
        return abc_subclasshook_check(
            Writer, cls, subclass, names=(cls.write.__name__,)
        )


@Writer.register
class ClearWriter:
    """Writer that clears generated sections or flashcard state values.

    Use as an async context manager; on exit the appropriate sections are
    updated/truncated depending on the requested `ClearType`.
    """

    __slots__: ClassVar = ("__options", "__path")
    __FLASHCARD_STATES_REGEX: ClassVar = re.compile(
        r" ?" + FLASHCARD_STATES_REGEX.pattern, FLASHCARD_STATES_REGEX.flags
    )

    def __init__(self, path: Path, *, options: ClearOpts) -> None:
        """Create a `ClearWriter` for `path` with the given `options`."""
        self.__path = path
        self.__options = options

    @asynccontextmanager
    async def write(self) -> AsyncIterator[None]:
        """Return an async context manager which clears the file per options.

        The returned context manager yields control to the caller and performs
        clearing work on exit.
        """
        if ClearType.CONTENT in self.__options.types:

            async def process(io: AnyTextIO) -> None:
                """Truncate content sections (clear content)."""
                await wrap_async(io.truncate())

        elif ClearType.FLASHCARD_STATE in self.__options.types:

            async def process(io: AnyTextIO) -> None:
                """Strip flashcard state markers from the section content."""
                read = await wrap_async(io.read())
                await wrap_async(io.seek(0))
                if (text := self.__FLASHCARD_STATES_REGEX.sub("", read)) != read:
                    await wrap_async(io.write(text))
                    await wrap_async(io.truncate())
        else:

            async def process(io: AnyTextIO) -> None:
                """No-op processor for unrecognized clear types."""
                pass

        try:
            yield
        finally:
            async with lock_file(self.__path):
                for section in await FileSection.find(self.__path):
                    async with FileSection(
                        path=self.__path, section=section
                    ).open() as io:
                        await process(io)


assert issubclass(ClearWriter, Writer)


@Writer.register
class PythonWriter:
    """Writer that executes code in the provided `Environment` and writes results.

    The `write` context manager runs the code and collects `Result` objects
    which are then written into their target locations.
    """

    __slots__: ClassVar = ("__code", "__env", "__init_codes", "__options")

    def __init__(
        self,
        code: CodeType,
        /,
        *,
        init_codes: Iterable[CodeType],
        env: Environment,
        options: GenOpts,
    ) -> None:
        """Create a `PythonWriter` which will execute `code` in `env`.

        `init_codes` are executed before `code` and may initialize environment
        state used by the primary code object.
        """
        self.__code = code
        self.__init_codes = tuple(init_codes)
        self.__env = env
        self.__options = options

    def __repr__(self) -> str:
        """Return an unambiguous representation for debugging and tests."""
        return f"{type(self).__qualname__}({self.__code!r}, env={self.__env!r}, options={self.__options!r})"

    def __str__(self) -> str:
        """Return a concise, human-friendly string for the writer."""
        return f"{type(self).__qualname__}({self.__code}, env={self.__env}, options={self.__options})"

    @asynccontextmanager
    async def write(self) -> AsyncIterator[None]:
        """Execute the code and write each resulting `Result` to its location."""

        def results0(result: Any) -> Iterable[Result]:
            """Normalize the writer execution result to an iterator of `Result`."""
            if Result.isinstance(result):
                yield result
                return
            if isinstance(result, Iterable):
                result0: Iterable[Any] = cast(Iterable[Any], result)
                for item in result0:
                    if not Result.isinstance(item):
                        raise TypeError(item)
                    yield item
                return
            raise TypeError(result)

        results = results0(await self.__env.exec(self.__code, *self.__init_codes))
        try:
            yield
        finally:
            # Group results by their target path and write combined content per
            # target. Multiple `Result` objects for the same location should
            # result in a single write containing their concatenation (in the
            # returned order); empty-result entries are ignored.
            results = tuple(results)
            groups: dict[Location, MutableSequence[Result]] = {}
            for r in results:
                groups.setdefault(r.location, []).append(r)

            async def process_group(group: Sequence[Result]) -> None:
                """Write concatenated `Result` content for a single target `Location`.

                Uses file locking when appropriate and only updates the file when the
                concatenated text differs from the existing generated section.
                """
                loc = group[0].location
                path = loc.path
                async with nullcontext() if path is None else lock_file(path):
                    async with loc.open() as io:
                        read = await wrap_async(io.read())
                        await wrap_async(io.seek(0))
                        timestamp = GENERATE_COMMENT_REGEX.search(read)
                        compare = (
                            read[: timestamp.start()] + read[timestamp.end() :]
                            if timestamp
                            else read
                        )
                        combined = "".join(r.text for r in group if r.text != "")
                        if combined and combined != compare:
                            text = (
                                GENERATE_COMMENT_FORMAT.format(
                                    now=datetime.now().astimezone().isoformat()
                                )
                                if self.__options.timestamp
                                else timestamp[0]
                                if timestamp
                                else ""
                            ) + combined
                            await wrap_async(io.write(text))
                            await wrap_async(io.truncate())

            await gather(*map(process_group, groups.values()))


assert issubclass(PythonWriter, Writer)
