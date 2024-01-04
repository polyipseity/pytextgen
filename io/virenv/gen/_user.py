# -*- coding: UTF-8 -*-
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
from dataclasses import dataclass as _dc
from functools import partial as _partial
from html import unescape as _unescape
from itertools import chain as _chain
from re import (
    DOTALL as _DOTALL,
    Match as _Match,
    NOFLAG as _NOFLAG,
    Pattern as _Pattern,
    compile as _re_comp,
)
from typing import (
    Any as _Any,
    Callable as _Call,
    Iterable as _Iter,
    Iterator as _Itor,
    Literal as _Lit,
    Mapping as _Map,
    Sequence as _Seq,
    TypeVar as _TVar,
    final as _fin,
)

_T = _TVar("_T")

_SECTION_TEXT_FORMAT = "\n\n{}\n\n"
_TABLE_ALIGNS: _Map[_Lit["default", "left", "right", "center"], str] = {
    "default": "-",
    "left": ":-",
    "right": "-:",
    "center": ":-:",
}


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
class _MarkdownRegex:
    regex: _Pattern[str]
    desugared: str


_MARKDOWN_REGEXES = (
    _MarkdownRegex(regex=_re_comp(r"(?:\b|^)__(?=\S)", _NOFLAG), desugared="<b u>"),
    _MarkdownRegex(regex=_re_comp(r"(?<=\S)__(?:\b|$)", _NOFLAG), desugared="</b u>"),
    _MarkdownRegex(regex=_re_comp(r"\*\*(?=\S)", _NOFLAG), desugared="<b s>"),
    _MarkdownRegex(regex=_re_comp(r"(?<=\S)\*\*", _NOFLAG), desugared="</b s>"),
    _MarkdownRegex(regex=_re_comp(r"(?:\b|^)_(?=\S)", _NOFLAG), desugared="<i u>"),
    _MarkdownRegex(regex=_re_comp(r"(?<=\S)_(?:\b|$)", _NOFLAG), desugared="</i u>"),
    _MarkdownRegex(regex=_re_comp(r"\*(?=\S)", _NOFLAG), desugared="<i s>"),
    _MarkdownRegex(regex=_re_comp(r"(?<=\S)\*", _NOFLAG), desugared="</i s>"),
    _MarkdownRegex(
        regex=_re_comp(r"\[(.*?(?<!\\))\]\(.*?(?<!\\)\)", _DOTALL),
        desugared=R"<a>\1</a>",
    ),
)
_HTML_TAG_REGEX = _re_comp(r"<([^>]+)>", _NOFLAG)


def text(text: str):
    return _Unit(text).map(_strp_ls).map(_SECTION_TEXT_FORMAT.format).counit()


_TEXT = text


def quote(text: str, prefix: str = "> "):
    return _Unit(text).map(_partial(_afx_ls, prefix=prefix)).counit()


def quotette(text: str, prefix: str = "> "):
    return _Unit(text).map(_partial(quote, prefix=prefix)).map(_TEXT).counit()


def quote_text(code: _TextCode, /, *, tag: str = _Tag.TEXT, line_prefix: str = "> "):
    return (
        _Unit(code)
        .map(_partial(_c2s, tag=tag))
        .map(_partial(quotette, prefix=line_prefix))
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
    states: _Iter[_FcStGrp],
):
    return (
        _Unit(code)
        .map(_partial(_sep_c_by_t, tag=sep_tag))
        .map(lambda codes: map(_partial(_c2s, tag=tag), codes))
        .map(_partial(_cz_txts, token=token))
        .map(_partial(_atch_fc_s, states=states))
        .map(lambda groups: map(str, groups))
        .map(lambda strs: map(_partial(quote, prefix=line_prefix), strs))
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
):
    if sep_tag is None:
        unit = _Unit(code).map(_partial(_c2ss, tag=tag))
    else:
        unit = (
            _Unit(code)
            .map(_partial(_sep_c_by_t, tag=sep_tag))
            .map(lambda codes: map(_partial(_c2s, tag=tag), codes))
        )
    if not empty:
        unit = unit.map(lambda strs: filter(lambda x: len(x) > 0, strs))
    return unit.counit()


def memorize(
    code: _TextCode,
    /,
    *,
    func: _Call[[_Iter[str]], _Iter[_FcGrp]],
    states: _Iter[_FcStGrp],
    tag: str = _Tag.MEMORIZE,
    sep_tag: str | None = None,
    empty: bool = False,
):
    return (
        _Unit(code)
        .map(_partial(tagged_filter_sep, tag=tag, sep_tag=sep_tag, empty=empty))
        .map(func)
        .map(_partial(_atch_fc_s, states=states))
        .map(_lsty_fc)
        .map(text)
        .counit()
    )


def memorize_two_sided(
    code: _TextCode,
    /,
    *,
    offsets: _Call[[int], int | None] | _Seq[int] | int = 1,
    hinter: _Call[[int, str], tuple[str, str]] = _const(("", "")),
    reversible: bool = True,
    **kwargs: _Any,
):
    return memorize(
        code,
        func=_partial(
            _mem_2s,
            offsets=(
                _const(offsets)
                if isinstance(offsets, int)
                else offsets.__getitem__
                if isinstance(offsets, _Seq)
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
    hinted: _Call[[int], bool] | _Seq[bool] | bool = True,
    sanitizer: _Call[[str], str] = _id,
    reversible: bool = True,
    **kwargs: _Any,
):
    return memorize(
        code,
        func=_partial(
            _mem_lkd_seq,
            reversible=reversible,
            hinter=_punct_htr(
                (
                    _const(hinted)
                    if isinstance(hinted, bool)
                    else hinted.__getitem__
                    if isinstance(hinted, _Seq)
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
    indices: _Call[[int], int | None] | _Seq[int | None] | int = 1,
    reversible: bool = True,
    **kwargs: _Any,
):
    return memorize(
        code,
        func=_partial(
            _mem_idx_seq,
            indices=(
                indices.__add__
                if isinstance(indices, int)
                else indices.__getitem__
                if isinstance(indices, _Seq)
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
    states: _Iter[_FcStGrp],
    tags: str | tuple[str, str] = _Tag.SEMANTICS,
    sep_tags: tuple[str | None, str | None] | str | None = None,
    empty: tuple[bool, bool] | bool = False,
    reversible: bool = False,
):
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
        .map(_partial(_sem_seq_map, reversible=reversible))
        .map(_partial(_atch_fc_s, states=states))
        .map(_lsty_fc)
        .map(text)
        .counit()
    )


def markdown_sanitizer(text: str):
    def get_and_del_tags(text: str):
        tags = set[str]()
        matches = list[_Match[str]]()

        stack = list[_Match[str]]()
        match: _Match[str]
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
        matches.sort(key=_Match[str].start)

        def ret_gen() -> _Itor[str]:
            prev: int = 0
            match: _Match[str]
            for match in matches:
                yield text[prev : match.start()]
                prev = match.end()
            yield text[prev:]

        return ("".join(ret_gen()), frozenset(tags))

    text, tags = get_and_del_tags(text)
    distingusher = "\0" * (len(max(tags, key=len, default="")) + 1)
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
    return _unescape(text)


def seq_to_code(
    seq: _Seq[str],
    /,
    *,
    index: int = 1,
    prefix: str = "",
    suffix: str = "",
    escape: bool = False,
):
    def gen_code():
        yield prefix
        newline = ""
        for idx, str_ in enumerate(seq):
            yield f"{{{_Tag.TEXT}:{newline}{index + idx}. }}{_TextCode.escape(str_, block=True) if escape else str_}"
            newline = "\n"
        yield suffix

    return _TextCode.compile("".join(gen_code()))


def map_to_code(
    map: _Map[str, str],
    /,
    *,
    name: str = "",
    token: tuple[str, str] = _CFG.cloze_token,
    name_cloze: bool = False,
    key_cloze: bool = False,
    value_cloze: bool = True,
):
    token = (_TextCode.escape(token[0]), _TextCode.escape(token[1]))
    name_token = token if name_cloze else ("", "")
    key_token = token if key_cloze else ("", "")
    value_token = token if value_cloze else ("", "")

    def gen_code():
        newline = ""
        if name:
            yield name_token[0]
            yield name
            yield name_token[1]
            yield "\n"
            newline = "\n"
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
    maps: _Map[str, _Map[str, str]],
    /,
    *,
    sep_tag: str = _Tag.CLOZE_SEPARATOR,
    **kwargs: _Any,
):
    def codegen():
        for key, value in maps.items():
            yield str(map_to_code(value, name=key, **kwargs))

    return _TextCode.compile(f"{{{_TextCode.escape(sep_tag)}:}}".join(codegen()))


def rows_to_table(
    rows: _Iter[_T],
    /,
    *,
    names: _Iter[str | tuple[str, _Lit["default", "left", "right", "center"]]],
    values: _Call[[_T], _Iter[_Any]],
):
    names0 = _IterSeq(iter(names))
    lf = "\n"
    return f"""| {' | '.join(name if isinstance(name, str) else name[0] for name in names0)} |
|{'|'.join(_TABLE_ALIGNS['default' if isinstance(name, str) else name[1]] for name in names0)}|
{lf.join(f'| {" | ".join(map(str, values(row)))} |' for row in rows)}"""


def two_columns_to_code(
    rows: _Iter[_T],
    /,
    *,
    left: _Call[[_T], str],
    right: _Call[[_T], str],
):
    return _TextCode.compile(
        "{}".join(
            item if item else "{:}"
            for item in _chain.from_iterable((left(row), right(row)) for row in rows)
        )
    )
