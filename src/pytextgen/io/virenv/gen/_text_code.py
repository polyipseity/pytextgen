from collections import defaultdict as _defdict
from dataclasses import KW_ONLY as _KW_ONLY
from dataclasses import dataclass as _dc
from re import NOFLAG as _NOFLAG
from re import compile as _re_comp
from re import escape as _re_esc
from typing import (
    Any as _Any,
)
from typing import (
    ClassVar as _ClsVar,
)
from typing import (
    Iterable as _Iter,
)
from typing import (
    Literal as _Lit,
)
from typing import (
    MutableSequence as _MSeq,
)
from typing import (
    Self as _Self,
)
from typing import (
    final as _fin,
)
from typing import (
    overload as _overload,
)

from ..util import constant as _const
from ._misc import Tag as _Tag

__all__ = (
    "TextCode",
    "code_to_strs",
    "code_to_str",
    "affix_code",
    "separate_code_by_tag",
)


@_fin
class TextCode:
    __slots__: _ClsVar = ("__blocks", "__by_tag")
    ESCAPES: _ClsVar = frozenset({"\\", "{", "}", ":"})
    ESCAPE_REGEX: _ClsVar = _re_comp(rf"{'|'.join(map(_re_esc, ESCAPES))}", _NOFLAG)

    @_fin
    @_dc(
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
        text: str
        _: _KW_ONLY
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

    @_fin
    @_dc(
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

    def __init__(self, blocks: _Iter[Block]):
        self.__blocks = tuple(blocks)
        by_tag = _defdict[str, _MSeq[TextCode.ByTagValue]](list)
        for idx, block in enumerate(self.blocks):
            by_tag[block.tag].append(TextCode.ByTagValue(idx=idx, block=block))
        self.__by_tag = _defdict(_const(()), {k: tuple(v) for k, v in by_tag.items()})

    def __repr__(self):
        return f"{type(self).__qualname__}(blocks={self.blocks!r})"

    def __str__(self):
        return "".join(map(str, self.blocks))

    @property
    def blocks(self):
        return self.__blocks

    @property
    def by_tag(self):
        return self.__by_tag

    @classmethod
    def escape(cls, text: str, /, *, block: bool = False):
        ret = cls.ESCAPE_REGEX.sub(lambda match: Rf"\{match[0]}", text)
        return f"{{:{ret}}}" if block else ret

    @_fin
    @_dc(
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
        Tag = _Lit["block", "escape", "normal", "tag"]
        __Tag0 = _Lit["normal", "tag"]
        __Tag1 = _Lit["block"]
        __Tag2 = _Lit["escape"]
        tag: Tag
        data: _Any

        @_overload
        @classmethod
        def wrap(cls, tag: __Tag0, data: str) -> _Self: ...

        @_overload
        def unwrap(self, tag: __Tag0) -> str: ...

        @_overload
        def mutate(self, tag: __Tag0, data: str) -> None: ...

        @_overload
        @classmethod
        def wrap(cls, tag: __Tag1, data: tuple[str, str]) -> _Self: ...

        @_overload
        def unwrap(self, tag: __Tag1) -> tuple[str, str]: ...

        @_overload
        def mutate(self, tag: __Tag1, data: tuple[str, str]) -> None: ...

        @_overload
        @classmethod
        def wrap(cls, tag: __Tag2, data: __Tag0 | __Tag1) -> _Self: ...

        @_overload
        def unwrap(self, tag: __Tag2) -> __Tag0 | __Tag1: ...

        @_overload
        def mutate(self, tag: __Tag2, data: __Tag0 | __Tag1) -> None: ...

        @classmethod
        def wrap(cls, tag: Tag, data: _Any):
            return cls(tag=tag, data=data)

        def unwrap(self, tag: Tag):
            return self.data

        def mutate(self, tag: Tag, data: _Any):
            self.data = data

    @classmethod
    def compiler(cls, code: str):
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
        return cls(cls.compiler(text))


def code_to_strs(code: TextCode, /, *, tag: str = _Tag.COMMON):
    return (block.text for block in code.blocks if block.common or block.tag == tag)


def code_to_str(code: TextCode, /, *, tag: str = _Tag.COMMON):
    return "".join(code_to_strs(code, tag=tag))


def affix_code(code: TextCode, /, *, prefix: str = "", suffix: str = ""):
    return code.compile("".join((prefix, str(code), suffix)))


def separate_code_by_tag(code: TextCode, /, *, tag: str):
    source: str = str(code)
    cur: int | None = None
    index: int
    for index in (block.block.char for block in code.by_tag[tag]):
        yield code.compile(source[cur:index])
        cur = index
    yield code.compile(source[cur:])
