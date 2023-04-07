# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import functools as _functools
import html as _html
import itertools as _itertools
import re as _re
import types as _types
import typing as _typing

from ..config import CONFIG as _CFG
from ..util import (
    FlashcardGroup as _FcGrp,
    FlashcardStateGroup as _FcStGrp,
    IteratorSequence as _IterSeq,
    Unit as _Unit,
    affix_lines as _afx_ls,
    constant as _const,
    identity as _id,
    strip_lines as _strp_ls,
)
from ._flashcard import (
    attach_flashcard_states as _atch_fc_s,
    cloze_texts as _cz_txts,
    listify_flashcards as _lsty_fc,
    memorize_indexed_seq0 as _mem_idx_seq,
    memorize_linked_seq0 as _mem_lkd_seq,
    memorize_two_sided0 as _mem_2s,
    punctuation_hinter as _punct_htr,
    semantics_seq_map0 as _sem_seq_map,
)
from ._misc import Tag as _Tag
from ._text_code import (
    TextCode as _TextCode,
    code_to_str as _c2s,
    code_to_strs as _c2ss,
    separate_code_by_tag as _sep_c_by_t,
)

_T = _typing.TypeVar("_T")

_SECTION_TEXT_FORMAT = "\n\n{}\n\n"
_TABLE_ALIGNS: _typing.Mapping[
    _typing.Literal["default", "left", "right", "center"], str
] = _types.MappingProxyType(
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


_MARKDOWN_REGEXES: _typing.Sequence[_MarkdownRegex] = (
    _MarkdownRegex(
        regex=_re.compile(r"(?:\b|^)__(?=\S)", flags=_re.NOFLAG), desugared="<b u>"
    ),
    _MarkdownRegex(
        regex=_re.compile(r"(?<=\S)__(?:\b|$)", flags=_re.NOFLAG), desugared="</b u>"
    ),
    _MarkdownRegex(
        regex=_re.compile(r"\*\*(?=\S)", flags=_re.NOFLAG), desugared="<b s>"
    ),
    _MarkdownRegex(
        regex=_re.compile(r"(?<=\S)\*\*", flags=_re.NOFLAG), desugared="</b s>"
    ),
    _MarkdownRegex(
        regex=_re.compile(r"(?:\b|^)_(?=\S)", flags=_re.NOFLAG), desugared="<i u>"
    ),
    _MarkdownRegex(
        regex=_re.compile(r"(?<=\S)_(?:\b|$)", flags=_re.NOFLAG), desugared="</i u>"
    ),
    _MarkdownRegex(regex=_re.compile(r"\*(?=\S)", flags=_re.NOFLAG), desugared="<i s>"),
    _MarkdownRegex(
        regex=_re.compile(r"(?<=\S)\*", flags=_re.NOFLAG), desugared="</i s>"
    ),
    _MarkdownRegex(
        regex=_re.compile(r"\[(.*?(?<!\\))\]\(.*?(?<!\\)\)", flags=_re.DOTALL),
        desugared=R"<a>\1</a>",
    ),
)
_HTML_TAG_REGEX = _re.compile(r"<([^>]+)>", flags=_re.NOFLAG)


def text(text: str) -> str:
    return _Unit(text).map(_strp_ls).map(_SECTION_TEXT_FORMAT.format).counit()


_TEXT = text


def quote(text: str, prefix: str = "> ") -> str:
    return _Unit(text).map(_functools.partial(_afx_ls, prefix=prefix)).counit()


def quotette(text: str, prefix: str = "> ") -> str:
    return _Unit(text).map(_functools.partial(quote, prefix=prefix)).map(_TEXT).counit()


def quote_text(
    code: _TextCode,
    /,
    *,
    tag: str = _Tag.TEXT,
    line_prefix: str = "> ",
) -> str:
    return (
        _Unit(code)
        .map(_functools.partial(_c2s, tag=tag))
        .map(_functools.partial(quotette, prefix=line_prefix))
        .counit()
    )


def cloze_text(
    code: _TextCode,
    /,
    *,
    tag: str = _Tag.TEXT,
    sep_tag: str = _Tag.CLOZE_SEPARATOR,
    token: tuple[str, str] = _CFG.cloze_token,
    line_prefix: str = "> ",
    separator: str = "\n\n",
    states: _typing.Iterable[_FcStGrp],
) -> str:
    return (
        _Unit(code)
        .map(_functools.partial(_sep_c_by_t, tag=sep_tag))
        .map(lambda codes: map(_functools.partial(_c2s, tag=tag), codes))
        .map(_functools.partial(_cz_txts, token=token))
        .map(_functools.partial(_atch_fc_s, states=states))
        .map(lambda groups: map(str, groups))
        .map(lambda strs: map(_functools.partial(quote, prefix=line_prefix), strs))
        .map(separator.join)
        .map(text)
        .counit()
    )


def tagged_filter_sep(
    code: _TextCode,
    /,
    *,
    tag: str,
    sep_tag: str | None = None,
    empty: bool = False,
) -> _typing.Iterator[str]:
    if sep_tag is None:
        unit = _Unit(code).map(_functools.partial(_c2ss, tag=tag))
    else:
        unit = (
            _Unit(code)
            .map(_functools.partial(_sep_c_by_t, tag=sep_tag))
            .map(lambda codes: map(_functools.partial(_c2s, tag=tag), codes))
        )
    if not empty:
        unit = unit.map(lambda strs: filter(lambda x: len(x) > 0, strs))
    return unit.counit()


def memorize(
    code: _TextCode,
    /,
    *,
    func: _typing.Callable[[_typing.Iterable[str]], _typing.Iterable[_FcGrp]],
    states: _typing.Iterable[_FcStGrp],
    tag: str = _Tag.MEMORIZE,
    sep_tag: str | None = None,
    empty: bool = False,
) -> str:
    return (
        _Unit(code)
        .map(
            _functools.partial(tagged_filter_sep, tag=tag, sep_tag=sep_tag, empty=empty)
        )
        .map(func)
        .map(_functools.partial(_atch_fc_s, states=states))
        .map(_lsty_fc)
        .map(text)
        .counit()
    )


def memorize_two_sided(
    code: _TextCode,
    /,
    *,
    offsets: _typing.Callable[[int], int | None] | _typing.Sequence[int] | int = 1,
    hinter: _typing.Callable[[int, str], tuple[str, str]] = _const(("", "")),
    reversible: bool = True,
    **kwargs: _typing.Any,
) -> str:
    return memorize(
        code,
        func=_functools.partial(
            _mem_2s,
            offsets=(
                _const(offsets)
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
    code: _TextCode,
    /,
    *,
    hinted: _typing.Callable[[int], bool] | _typing.Sequence[bool] | bool = True,
    sanitizer: _typing.Callable[[str], str] = _id,
    reversible: bool = True,
    **kwargs: _typing.Any,
) -> str:
    return memorize(
        code,
        func=_functools.partial(
            _mem_lkd_seq,
            reversible=reversible,
            hinter=_punct_htr(
                (
                    _const(hinted)
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
    code: _TextCode,
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
            _mem_idx_seq,
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
    code: _TextCode,
    sem: _TextCode,
    *,
    states: _typing.Iterable[_FcStGrp],
    tags: str | tuple[str, str] = _Tag.SEMANTICS,
    sep_tags: tuple[str | None, str | None] | str | None = None,
    empty: tuple[bool, bool] | bool = False,
    reversible: bool = False,
) -> str:
    if not isinstance(tags, tuple):
        tags = (tags, tags)
    if not isinstance(sep_tags, tuple):
        sep_tags = (sep_tags, sep_tags)
    if not isinstance(empty, tuple):
        empty = (empty, empty)
    return (
        _Unit((code, sem))
        .map(
            lambda codes: (
                tagged_filter_sep(
                    codes[0], tag=tags[0], sep_tag=sep_tags[0], empty=empty[0]
                ),
                tagged_filter_sep(
                    codes[1], tag=tags[1], sep_tag=sep_tags[1], empty=empty[1]
                ),
            )
        )
        .map(lambda strss: zip(*strss, strict=True))
        .map(_functools.partial(_sem_seq_map, reversible=reversible))
        .map(_functools.partial(_atch_fc_s, states=states))
        .map(_lsty_fc)
        .map(text)
        .counit()
    )


def markdown_sanitizer(text: str) -> str:
    def get_and_del_tags(text: str) -> tuple[str, _typing.AbstractSet[str]]:
        tags: _typing.MutableSet[str] = set()
        matches: _typing.MutableSequence[_re.Match[str]] = []

        stack: _typing.MutableSequence[_re.Match[str]] = []
        match: _re.Match[str]
        for match in _HTML_TAG_REGEX.finditer(text):
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

    text, tags = get_and_del_tags(text)
    distingusher: str = "\0" * (len(max(tags, key=len, default="")) + 1)
    for regex in _MARKDOWN_REGEXES:
        text = regex.regex.sub(
            _HTML_TAG_REGEX.sub(
                lambda m: f"<{m[1][:-1]}{distingusher}/>"
                if m[1].endswith("/")
                else f"<{m[1]}{distingusher}>",
                regex.desugared,
            ),
            text,
        )
    text, _ = get_and_del_tags(text)
    return _html.unescape(text)


def seq_to_code(
    seq: _typing.Sequence[str],
    /,
    *,
    index: int = 1,
    prefix: str = "",
    suffix: str = "",
    escape: bool = False,
) -> _TextCode:
    def gen_code() -> _typing.Iterator[str]:
        yield prefix
        newline: str = ""
        idx: int
        str_: str
        for idx, str_ in enumerate(seq):
            yield f"{{{_Tag.TEXT}:{newline}{index + idx}. }}{_TextCode.escape(str_, block=True) if escape else str_}"
            newline = "\n"
        yield suffix

    return _TextCode.compile("".join(gen_code()))


def map_to_code(
    map: _typing.Mapping[str, str],
    /,
    *,
    name: str = "",
    token: tuple[str, str] = _CFG.cloze_token,
    name_cloze: bool = False,
    key_cloze: bool = False,
    value_cloze: bool = True,
) -> _TextCode:
    token = (_TextCode.escape(token[0]), _TextCode.escape(token[1]))
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

    return _TextCode.compile("".join(gen_code()))


def maps_to_code(
    maps: _typing.Mapping[str, _typing.Mapping[str, str]],
    /,
    *,
    sep_tag: str = _Tag.CLOZE_SEPARATOR,
    **kwargs: _typing.Any,
) -> _TextCode:
    def codegen() -> _typing.Iterator[str]:
        key: str
        value: _typing.Mapping[str, str]
        for key, value in maps.items():
            yield str(map_to_code(value, name=key, **kwargs))

    return _TextCode.compile(f"{{{_TextCode.escape(sep_tag)}:}}".join(codegen()))


def rows_to_table(
    rows: _typing.Iterable[_T],
    /,
    *,
    names: _typing.Iterable[
        str | tuple[str, _typing.Literal["default", "left", "right", "center"]]
    ],
    values: _typing.Callable[[_T], _typing.Iterable[_typing.Any]],
) -> str:
    names0 = _IterSeq(iter(names))
    lf = "\n"
    return f"""| {' | '.join(name if isinstance(name, str) else name[0] for name in names0)} |
|{'|'.join(_TABLE_ALIGNS['default' if isinstance(name, str) else name[1]] for name in names0)}|
{lf.join(f'| {" | ".join(map(str, values(row)))} |' for row in rows)}"""


def two_columns_to_code(
    rows: _typing.Iterable[_T],
    /,
    *,
    left: _typing.Callable[[_T], str],
    right: _typing.Callable[[_T], str],
) -> _TextCode:
    return _TextCode.compile(
        "{}".join(
            item if item else "{:}"
            for item in _itertools.chain.from_iterable(
                (left(row), right(row)) for row in rows
            )
        )
    )
