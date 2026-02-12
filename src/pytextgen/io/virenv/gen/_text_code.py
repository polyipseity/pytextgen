"""Helpers for creating, parsing and formatting small text-based codes.

`TextCode` provides a compact representation of tagged/escaped text blocks
used in generated content.
"""

from collections import defaultdict
from dataclasses import KW_ONLY, dataclass
from re import NOFLAG
from re import compile as re_compile
from re import escape as re_escape
from typing import (
    Any,
    ClassVar,
    Iterable,
    Literal,
    MutableSequence,
    Self,
    final,
    overload,
)

from ..util import constant
from ._misc import Tag

__all__ = (
    "TextCode",
    "code_to_strs",
    "code_to_str",
    "affix_code",
    "separate_code_by_tag",
)


@final
class TextCode:
    """Representation of text divided into `Block` elements.

    Blocks may be ordinary text or specially tagged blocks that are
    escaped and serialized with `{tag:...}` syntax.
    """

    __slots__: ClassVar = ("__blocks", "__by_tag")
    ESCAPES: ClassVar = frozenset({"\\", "{", "}", ":"})
    ESCAPE_REGEX: ClassVar = re_compile(rf"{'|'.join(map(re_escape, ESCAPES))}", NOFLAG)

    @final
    @dataclass(
        init=True,
        repr=True,
        eq=True,
        order=False,
        unsafe_hash=False,
        frozen=True,
        match_args=True,
        kw_only=False,
        slots=True,
    )
    class Block:
        """A single block of text inside a `TextCode`.

        `tag` indicates a special block when non-empty; `char` is the
        original character index used for splitting by tag.
        """

        text: str
        _: KW_ONLY
        char: int
        tag: str = ""

        @property
        def special(self):
            return bool(self.tag)

        @property
        def common(self):
            return not self.special

        def __str__(self):
            if self.special:
                return f"{{{self.tag}:{TextCode.escape(self.text)}}}"
            if self.text:
                return TextCode.escape(self.text)
            return "{:}"

    @final
    @dataclass(
        init=True,
        repr=True,
        eq=True,
        order=False,
        unsafe_hash=False,
        frozen=True,
        match_args=True,
        kw_only=True,
        slots=True,
    )
    class ByTagValue:
        idx: int
        block: "TextCode.Block"

    def __init__(self, blocks: Iterable[Block]):
        """Create a `TextCode` instance from an iterable of `Block` elements."""
        self.__blocks = tuple(blocks)
        by_tag = defaultdict[str, MutableSequence[TextCode.ByTagValue]](list)
        for idx, block in enumerate(self.blocks):
            by_tag[block.tag].append(TextCode.ByTagValue(idx=idx, block=block))
        self.__by_tag = defaultdict(
            constant(()), {k: tuple(v) for k, v in by_tag.items()}
        )

    def __repr__(self):
        """Return a detailed representation including contained blocks."""
        return f"{type(self).__qualname__}(blocks={self.blocks!r})"

    def __str__(self):
        """Serialize the `TextCode` back to its textual representation."""
        return "".join(map(str, self.blocks))

    @property
    def blocks(self):
        """Return the tuple of `Block` elements comprising this `TextCode`."""
        return self.__blocks

    @property
    def by_tag(self):
        """Return a mapping of tag -> sequence of `ByTagValue` entries."""
        return self.__by_tag

    @classmethod
    def escape(cls, text: str, /, *, block: bool = False):
        """Escape special characters in `text`.

        When `block=True` the escaped text is wrapped as a block `{:{escaped}}`.
        """
        ret = cls.ESCAPE_REGEX.sub(lambda match: Rf"\{match[0]}", text)
        return f"{{:{ret}}}" if block else ret

    @final
    @dataclass(
        init=True,
        repr=True,
        eq=True,
        order=False,
        unsafe_hash=False,
        frozen=False,
        match_args=True,
        kw_only=True,
        slots=True,
    )
    class __CompilerState:
        Tag = Literal["block", "escape", "normal", "tag"]
        __Tag0 = Literal["normal", "tag"]
        __Tag1 = Literal["block"]
        __Tag2 = Literal["escape"]
        tag: Tag
        data: Any

        @overload
        @classmethod
        def wrap(cls, tag: __Tag0, data: str) -> Self: ...

        @overload
        def unwrap(self, tag: __Tag0) -> str: ...

        @overload
        def mutate(self, tag: __Tag0, data: str) -> None: ...

        @overload
        @classmethod
        def wrap(cls, tag: __Tag1, data: tuple[str, str]) -> Self: ...

        @overload
        def unwrap(self, tag: __Tag1) -> tuple[str, str]: ...

        @overload
        def mutate(self, tag: __Tag1, data: tuple[str, str]) -> None: ...

        @overload
        @classmethod
        def wrap(cls, tag: __Tag2, data: __Tag0 | __Tag1) -> Self: ...

        @overload
        def unwrap(self, tag: __Tag2) -> __Tag0 | __Tag1: ...

        @overload
        def mutate(self, tag: __Tag2, data: __Tag0 | __Tag1) -> None: ...

        @classmethod
        def wrap(cls, tag: Tag, data: Any):
            return cls(tag=tag, data=data)

        def unwrap(self, tag: Tag):
            return self.data

        def mutate(self, tag: Tag, data: Any):
            self.data = data

    @classmethod
    def compiler(cls, code: str):
        """Compile a raw `code` string into a sequence of `Block` elements.

        This generator handles escaping and tagged blocks and yields `Block`
        objects in order.
        """
        stack = list[TextCode.__CompilerState]()
        stack.append(cls.__CompilerState.wrap("normal", ""))
        for index, char in enumerate(
            (code + "{}")
            if not code.endswith("}") or code.endswith(R"\}") or code.endswith("{}")
            else code
        ):
            state = stack[-1]
            if state.tag == "normal":
                if char == "\\":
                    stack.append(cls.__CompilerState.wrap("escape", state.tag))
                elif char == "{":
                    text = state.unwrap(state.tag)
                    if text:
                        yield TextCode.Block(text, char=index - len(text))
                        state.mutate(state.tag, "")
                    stack.append(cls.__CompilerState.wrap("tag", ""))
                elif char == "}":
                    raise ValueError(f"Unexpected char at {index}: {code}")
                else:
                    state.mutate(state.tag, f"{state.unwrap(state.tag)}{char}")
            elif state.tag == "escape":
                prev_tag = state.unwrap(state.tag)
                stack.pop()
                prev_state = stack[-1]
                if prev_tag == "block":
                    aa, bb = prev_state.unwrap(prev_tag)
                    prev_state.mutate(prev_tag, (aa, f"{bb}{char}"))
                else:
                    prev_state.mutate(prev_tag, f"{prev_state.unwrap(prev_tag)}{char}")
            elif state.tag == "tag":
                if char == "\\":
                    stack.append(cls.__CompilerState.wrap("escape", state.tag))
                elif char == "{":
                    raise ValueError(f"Unexpected char at {index}: {code}")
                elif char == ":":
                    stack[-1] = cls.__CompilerState.wrap(
                        "block", (state.unwrap(state.tag), "")
                    )
                elif char == "}":
                    text = state.unwrap(state.tag)
                    if text:
                        raise ValueError(f"Unexpected char at {index}: {code}")
                    stack.pop()
                else:
                    state.mutate(state.tag, f"{state.unwrap(state.tag)}{char}")
            elif state.tag == "block":
                if char == "\\":
                    stack.append(cls.__CompilerState.wrap("escape", state.tag))
                elif char == "{" or char == ":":
                    raise ValueError(f"Unexpected char at {index}: {code}")
                elif char == "}":
                    tag, text = state.unwrap(state.tag)
                    yield TextCode.Block(
                        text,
                        char=index - len("{") - len(tag) - len(":") - len(text),
                        tag=tag,
                    )
                    stack.pop()
                else:
                    aa, bb = state.unwrap(state.tag)
                    state.mutate(state.tag, (aa, f"{bb}{char}"))
            else:
                raise ValueError(f'Unexpected state "{state}": {code}')

    @classmethod
    def compile(cls, text: str):
        """Compile textual `text` into a `TextCode` composed of `Block`s."""
        return cls(cls.compiler(text))


def code_to_strs(code: TextCode, /, *, tag: str = Tag.COMMON):
    """Yield raw text strings from `code` for blocks matching `tag`."""
    return (block.text for block in code.blocks if block.common or block.tag == tag)


def code_to_str(code: TextCode, /, *, tag: str = Tag.COMMON):
    """Return a single string composed of matching `code` blocks."""
    return "".join(code_to_strs(code, tag=tag))


def affix_code(code: TextCode, /, *, prefix: str = "", suffix: str = ""):
    """Wrap `code` with `prefix` and `suffix` and re-compile it."""
    return code.compile("".join((prefix, str(code), suffix)))


def separate_code_by_tag(code: TextCode, /, *, tag: str):
    """Yield compiled `TextCode` segments separated by the given `tag`."""
    source: str = str(code)
    cur: int | None = None
    index: int
    for index in (block.block.char for block in code.by_tag[tag]):
        yield code.compile(source[cur:index])
        cur = index
    yield code.compile(source[cur:])
