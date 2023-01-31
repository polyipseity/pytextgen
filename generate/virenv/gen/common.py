# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import functools as _functools
import html as _html
import itertools as _itertools
import re as _re
import types as _types
import typing as _typing

from .. import gen as _gen
from .. import util as _util
from . import *

_T = _typing.TypeVar("_T")

_section_text_format: str = "\n\n{}\n\n"
_table_aligns: _typing.Mapping[
    _typing.Literal["default", "left", "right", "center"], str
] = _types.MappingProxyType[_typing.Literal["default", "left", "right", "center"], str](
    {"default": "-", "left": ":-", "right": "-:", "center": ":-:"}
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
    kw_only=True,
    slots=True,
)
class _MarkdownRegex:
    regex: _re.Pattern[str]
    desugared: str


_markdown_regexes: _typing.Sequence[_MarkdownRegex] = (
    _MarkdownRegex(regex=_re.compile(r"(?:\b|^)__(?=\S)", flags=0), desugared="<b u>"),
    _MarkdownRegex(
        regex=_re.compile(r"(?<=\S)__(?:\b|$)", flags=0), desugared="</b u>"
    ),
    _MarkdownRegex(regex=_re.compile(r"\*\*(?=\S)", flags=0), desugared="<b s>"),
    _MarkdownRegex(regex=_re.compile(r"(?<=\S)\*\*", flags=0), desugared="</b s>"),
    _MarkdownRegex(regex=_re.compile(r"(?:\b|^)_(?=\S)", flags=0), desugared="<i u>"),
    _MarkdownRegex(regex=_re.compile(r"(?<=\S)_(?:\b|$)", flags=0), desugared="</i u>"),
    _MarkdownRegex(regex=_re.compile(r"\*(?=\S)", flags=0), desugared="<i s>"),
    _MarkdownRegex(regex=_re.compile(r"(?<=\S)\*", flags=0), desugared="</i s>"),
)
_html_tag_regex: _re.Pattern[str] = _re.compile(r"<([^>]+)>", flags=0)


def text(text: str) -> str:
    return _util.Unit(text).map(strip_lines).map(_section_text_format.format).counit()


def quote_text(
    code: TextCode,
    /,
    *,
    tag: str = Tag.TEXT,
    line_prefix: str = "> ",
) -> str:
    return (
        _util.Unit(code)
        .map(_functools.partial(code_to_str, tag=tag))
        .map(_functools.partial(affix_lines, prefix=line_prefix))
        .map(text)
        .counit()
    )


def cloze_text(
    code: TextCode,
    /,
    *,
    tag: str = Tag.TEXT,
    sep_tag: str = Tag.CLOZE_SEPARATOR,
    token: tuple[str, str] = ("{{", "}}"),
    line_prefix: str = "> ",
    separator: str = "\n\n",
    states: _typing.Iterable[_util.FlashcardStateGroup],
) -> str:
    return (
        _util.Unit(code)
        .map(_functools.partial(separate_code_by_tag, tag=sep_tag))
        .map(lambda codes: map(_functools.partial(code_to_str, tag=tag), codes))
        .map(_functools.partial(cloze_texts, token=token))
        .map(_functools.partial(attach_flashcard_states, states=states))
        .map(lambda groups: map(str, groups))
        .map(
            lambda strs: map(_functools.partial(affix_lines, prefix=line_prefix), strs)
        )
        .map(separator.join)
        .map(text)
        .counit()
    )


def memorize(
    code: TextCode,
    /,
    *,
    func: _typing.Callable[
        [_typing.Iterable[str]], _typing.Iterable[_util.FlashcardGroup]
    ],
    states: _typing.Iterable[_util.FlashcardStateGroup],
    tag: str = Tag.MEMORIZE,
) -> str:
    return (
        _util.Unit(code)
        .map(_functools.partial(code_to_strs, tag=tag))
        .map(func)
        .map(_functools.partial(attach_flashcard_states, states=states))
        .map(listify_flashcards)
        .map(text)
        .counit()
    )


def memorize_two_sided(
    code: TextCode,
    /,
    *,
    offsets: _typing.Callable[[int], int | None] | _typing.Sequence[int] | int = 1,
    hinter: _typing.Callable[[int, str], tuple[str, str]] = _util.constant(("", "")),
    reversible: bool = True,
    **kwargs: _typing.Any,
) -> str:
    return memorize(
        code,
        func=_functools.partial(
            _gen.memorize_two_sided,
            offsets=(
                _util.constant(offsets)
                if isinstance(offsets, int)
                else offsets.__getitem__
                if isinstance(offsets, _typing.Sequence)
                else offsets
            ),
            reversible=reversible,
            hinter=hinter,
        ),
        **kwargs,
    )


def memorize_linked_seq(
    code: TextCode,
    /,
    *,
    hinted: _typing.Callable[[int], bool] | _typing.Sequence[bool] | bool = True,
    sanitizer: _typing.Callable[[str], str] = _util.identity,
    reversible: bool = True,
    **kwargs: _typing.Any,
) -> str:
    return memorize(
        code,
        func=_functools.partial(
            _gen.memorize_linked_seq,
            reversible=reversible,
            hinter=punctuation_hinter(
                (
                    _util.constant(hinted)
                    if isinstance(hinted, bool)
                    else hinted.__getitem__
                    if isinstance(hinted, _typing.Sequence)
                    else hinted
                ),
                sanitizer=sanitizer,
            ),
        ),
        **kwargs,
    )


def memorize_indexed_seq(
    code: TextCode,
    /,
    *,
    indices: _typing.Callable[[int], int | None]
    | _typing.Sequence[int | None]
    | int = 1,
    reversible: bool = True,
    **kwargs: _typing.Any,
) -> str:
    return memorize(
        code,
        func=_functools.partial(
            _gen.memorize_indexed_seq,
            indices=(
                indices.__add__
                if isinstance(indices, int)
                else indices.__getitem__
                if isinstance(indices, _typing.Sequence)
                else indices
            ),
            reversible=reversible,
        ),
        **kwargs,
    )


def semantics_seq_map(
    code: TextCode,
    sem: TextCode,
    *,
    states: _typing.Iterable[_util.FlashcardStateGroup],
    tag: str = Tag.SEMANTICS,
    reversible: bool = False,
) -> str:
    return (
        _util.Unit((code, sem))
        .map(
            lambda codes: (
                code_to_strs(codes[0], tag=tag),
                code_to_strs(codes[1], tag=tag),
            )
        )
        .map(lambda strss: zip(*strss, strict=True))
        .map(_functools.partial(_gen.semantics_seq_map, reversible=reversible))
        .map(_functools.partial(attach_flashcard_states, states=states))
        .map(listify_flashcards)
        .map(text)
        .counit()
    )


def markdown_sanitizer(text: str) -> str:
    text = _html.unescape(text)

    def get_and_remove_html_tags(text: str) -> tuple[str, _typing.AbstractSet[str]]:
        tags: _typing.MutableSet[str] = set()
        matches: _typing.MutableSequence[_re.Match[str]] = []

        stack: _typing.MutableSequence[_re.Match[str]] = []
        match: _re.Match[str]
        for match in _html_tag_regex.finditer(text):
            tag: str = match[1]
            if tag.startswith("/"):
                tag0: str = tag[1:]
                tags.add(tag0)
                if stack and stack[-1][1] == tag0:
                    matches.extend((stack.pop(), match))
            elif tag.endswith("/"):
                tag0: str = tag[:-1]
                tags.add(tag0)
                matches.append(match)
            else:
                tags.add(tag)
                stack.append(match)
        matches.sort(key=_re.Match[str].start)

        def ret_gen() -> _typing.Iterator[str]:
            prev: int = 0
            match: _re.Match[str]
            for match in matches:
                yield text[prev : match.start()]
                prev = match.end()
            yield text[prev:]

        return ("".join(ret_gen()), frozenset(tags))

    tags: _typing.AbstractSet[str]
    text, tags = get_and_remove_html_tags(text)
    distingusher: str = "\0" * (len(max(tags, key=len, default="")) + 1)
    md_regex: _MarkdownRegex
    for md_regex in _markdown_regexes:
        suffix: str = (
            "/>"
            if md_regex.desugared.endswith("/>")
            else ">"
            if md_regex.desugared.endswith(">")
            else ""
        )
        text = md_regex.regex.sub(
            f"{md_regex.desugared[:-len(suffix)]}{distingusher}{suffix}", text
        )
    text, _ = get_and_remove_html_tags(text)
    return text


def seq_to_code(
    seq: _typing.Sequence[str],
    /,
    *,
    index: int = 1,
    prefix: str = "",
    suffix: str = "",
    escape: bool = False,
) -> TextCode:
    def gen_code() -> _typing.Iterator[str]:
        yield prefix
        newline: str = ""
        idx: int
        str_: str
        for idx, str_ in enumerate(seq):
            yield "{text:"
            yield newline
            yield str(index + idx)
            yield ". }"
            yield TextCode.escape(str_, block=True) if escape else str_
            newline = "\n"
        yield suffix

    return TextCode.compile("".join(gen_code()))


def map_to_code(
    map: _typing.Mapping[str, str],
    /,
    *,
    name: str = "",
    token: tuple[str, str] = ("{{", "}}"),
    name_cloze: bool = False,
    key_cloze: bool = False,
    value_cloze: bool = True,
) -> TextCode:
    token = (TextCode.escape(token[0]), TextCode.escape(token[1]))
    name_token: tuple[str, str] = token if name_cloze else ("", "")
    key_token: tuple[str, str] = token if key_cloze else ("", "")
    value_token: tuple[str, str] = token if value_cloze else ("", "")

    def gen_code() -> _typing.Iterator[str]:
        newline: str = ""
        if name:
            yield name_token[0]
            yield name
            yield name_token[1]
            newline = "\n"
        key: str
        value: str
        for key, value in map.items():
            yield newline
            yield "- "
            yield key_token[0]
            yield key
            yield key_token[1]
            yield ": "
            yield value_token[0]
            yield value
            yield value_token[1]
            newline = "\n"

    return TextCode.compile("".join(gen_code()))


def maps_to_code(
    maps: _typing.Mapping[str, _typing.Mapping[str, str]],
    /,
    *,
    sep_tag: str = Tag.CLOZE_SEPARATOR,
    **kwargs: _typing.Any,
) -> TextCode:
    def codegen() -> _typing.Iterator[str]:
        key: str
        value: _typing.Mapping[str, str]
        for key, value in maps.items():
            yield str(map_to_code(value, name=key, **kwargs))

    return TextCode.compile(f"{{{TextCode.escape(sep_tag)}:}}".join(codegen()))


def rows_to_table(
    rows: _typing.Iterable[_T],
    /,
    *,
    names: _typing.Iterable[
        str | tuple[str, _typing.Literal["default", "left", "right", "center"]]
    ],
    values: _typing.Callable[[_T], _typing.Iterable[_typing.Any]],
) -> str:
    lf: str = "\n"
    return f"""{' | '.join(name if isinstance(name, str) else name[0] for name in names)}
{'|'.join(_table_aligns['default' if isinstance(name, str) else name[1]] for name in names)}
{lf.join(' | '.join(map(str, values(row))) for row in rows)}"""


def two_columns_to_code(
    rows: _typing.Iterable[_T],
    /,
    *,
    left: _typing.Callable[[_T], str],
    right: _typing.Callable[[_T], str],
) -> TextCode:
    return TextCode.compile(
        "{}".join(
            _itertools.chain.from_iterable((left(row), right(row)) for row in rows)
        )
    )
