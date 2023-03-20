# -*- coding: UTF-8 -*-
import collections as _collections
import dataclasses as _dataclasses
import re as _re
import types as _types
import typing as _typing

from ..util import constant as _const
from ._misc import Tag as _Tag


@_typing.final
class TextCode:
    __slots__: _typing.ClassVar = ("__blocks", "__by_tag")
    ESCAPES: _typing.ClassVar = frozenset({"\\", "{", "}", ":"})
    ESCAPE_REGEX: _typing.ClassVar = _re.compile(
        rf"{'|'.join(map(_re.escape, ESCAPES))}", flags=_re.NOFLAG
    )

    @_typing.final
    @_dataclasses.dataclass(
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
        _: _dataclasses.KW_ONLY
        char: int
        tag: str = ""

        @property
        def special(self) -> bool:
            return bool(self.tag)

        @property
        def common(self) -> bool:
            return not self.special

        def __str__(self) -> str:
            if self.special:
                return f"{{{self.tag}:{TextCode.escape(self.text)}}}"
            if self.text:
                return TextCode.escape(self.text)
            return "{:}"

    @_typing.final
    @_dataclasses.dataclass(
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

    def __init__(self, blocks: _typing.Iterable[Block]) -> None:
        self.__blocks: _typing.Sequence[TextCode.Block] = tuple(blocks)
        by_tag = _collections.defaultdict[
            str, _typing.MutableSequence[TextCode.ByTagValue]
        ](list)
        for idx, block in enumerate(self.blocks):
            by_tag[block.tag].append(TextCode.ByTagValue(idx=idx, block=block))
        self.__by_tag: _typing.Mapping[
            str, _typing.Sequence[TextCode.ByTagValue]
        ] = _types.MappingProxyType(
            _collections.defaultdict(
                _const(()), {k: tuple(v) for k, v in by_tag.items()}
            )
        )

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}(blocks={self.blocks!r})"

    def __str__(self) -> str:
        return "".join(map(str, self.blocks))

    @property
    def blocks(self) -> _typing.Sequence[Block]:
        return self.__blocks

    @property
    def by_tag(
        self,
    ) -> _typing.Mapping[str, _typing.Sequence[ByTagValue]]:
        return self.__by_tag

    @classmethod
    def escape(cls, text: str, /, *, block: bool = False) -> str:
        ret = cls.ESCAPE_REGEX.sub(lambda match: Rf"\{match[0]}", text)
        return f"{{:{ret}}}" if block else ret

    @_typing.final
    @_dataclasses.dataclass(
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
        Tag = _typing.Literal["block", "escape", "normal", "tag"]
        __Tag0 = _typing.Literal["normal", "tag"]
        __Tag1 = _typing.Literal["block"]
        __Tag2 = _typing.Literal["escape"]
        tag: Tag
        data: _typing.Any

        @_typing.overload
        @classmethod
        def wrap(cls, tag: __Tag0, data: str) -> _typing.Self:
            ...

        @_typing.overload
        def unwrap(self, tag: __Tag0) -> str:
            ...

        @_typing.overload
        def mutate(self, tag: __Tag0, data: str) -> None:
            ...

        @_typing.overload
        @classmethod
        def wrap(cls, tag: __Tag1, data: tuple[str, str]) -> _typing.Self:
            ...

        @_typing.overload
        def unwrap(self, tag: __Tag1) -> tuple[str, str]:
            ...

        @_typing.overload
        def mutate(self, tag: __Tag1, data: tuple[str, str]) -> None:
            ...

        @_typing.overload
        @classmethod
        def wrap(cls, tag: __Tag2, data: __Tag0 | __Tag1) -> _typing.Self:
            ...

        @_typing.overload
        def unwrap(self, tag: __Tag2) -> __Tag0 | __Tag1:
            ...

        @_typing.overload
        def mutate(self, tag: __Tag2, data: __Tag0 | __Tag1) -> None:
            ...

        @classmethod
        def wrap(cls, tag: Tag, data: _typing.Any):
            return cls(tag=tag, data=data)

        def unwrap(self, tag: Tag):
            return self.data

        def mutate(self, tag: Tag, data: _typing.Any):
            self.data = data

    @classmethod
    def compiler(cls, code: str) -> _typing.Iterator[Block]:
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
    def compile(cls, text: str) -> _typing.Self:
        return cls(cls.compiler(text))


def code_to_strs(code: TextCode, /, *, tag: str = _Tag.COMMON) -> _typing.Iterator[str]:
    return (block.text for block in code.blocks if block.common or block.tag == tag)


def code_to_str(code: TextCode, /, *, tag: str = _Tag.COMMON) -> str:
    return "".join(code_to_strs(code, tag=tag))


def affix_code(
    code: TextCode,
    /,
    *,
    prefix: str = "",
    suffix: str = "",
) -> TextCode:
    return code.compile("".join((prefix, str(code), suffix)))


def separate_code_by_tag(
    code: TextCode,
    /,
    *,
    tag: str,
) -> _typing.Iterator[TextCode]:
    source: str = str(code)
    cur: int | None = None
    index: int
    for index in (block.block.char for block in code.by_tag[tag]):
        yield code.compile(source[cur:index])
        cur = index
    yield code.compile(source[cur:])
