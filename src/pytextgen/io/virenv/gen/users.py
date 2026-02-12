"""User-facing generation helpers.

Functions in this module transform `TextCode` fragments into textual
representations for quoting, flashcards, tables, and other formatted
outputs used by the project.
"""

from dataclasses import dataclass
from functools import partial
from html import unescape
from itertools import chain
from re import DOTALL, NOFLAG, Match, Pattern
from re import compile as re_compile
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    Literal,
    Mapping,
    Sequence,
    TypeVar,
    final,
)
from unicodedata import normalize

from ..configs import CONFIG
from ..utils import (
    FlashcardGroup,
    FlashcardStateGroup,
    IteratorSequence,
    Unit,
    affix_lines,
    constant,
    identity,
    strip_lines,
)
from .flashcards import (
    attach_flashcard_states,
    cloze_texts,
    listify_flashcards,
    memorize_indexed_seq0,
    memorize_linked_seq0,
    memorize_two_sided0,
    punctuation_hinter,
    semantics_seq_map0,
)
from .misc import Tag
from .text_code import (
    TextCode,
    code_to_str,
    code_to_strs,
    separate_code_by_tag,
)

try:
    from wcwidth import wcswidth
except Exception:
    wcswidth = None

_T = TypeVar("_T")

__all__ = (
    "text",
    "quote",
    "quotette",
    "quote_text",
    "cloze_text",
    "tagged_filter_sep",
    "memorize",
    "memorize_two_sided",
    "memorize_linked_seq",
    "memorize_indexed_seq",
    "semantics_seq_map",
    "markdown_sanitizer",
    "seq_to_code",
    "map_to_code",
    "maps_to_code",
    "rows_to_table",
    "two_columns_to_code",
)

_SECTION_TEXT_FORMAT = "\n\n{}\n\n"
_TABLE_ALIGNS: Mapping[Literal["default", "left", "right", "center"], str] = {
    "default": "-",
    "left": ":-",
    "right": "-:",
    "center": ":-:",
}


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
class _MarkdownRegex:
    """Pair of compiled regex and its desugared replacement form used by sanitizer."""

    regex: Pattern[str]
    desugared: str


_MARKDOWN_REGEXES = (
    _MarkdownRegex(regex=re_compile(r"(?:\b|^)__(?=\S)", NOFLAG), desugared="<b u>"),
    _MarkdownRegex(regex=re_compile(r"(?<=\S)__(?:\b|$)", NOFLAG), desugared="</b u>"),
    _MarkdownRegex(regex=re_compile(r"\*\*(?=\S)", NOFLAG), desugared="<b s>"),
    _MarkdownRegex(regex=re_compile(r"(?<=\S)\*\*", NOFLAG), desugared="</b s>"),
    _MarkdownRegex(regex=re_compile(r"(?:\b|^)_(?=\S)", NOFLAG), desugared="<i u>"),
    _MarkdownRegex(regex=re_compile(r"(?<=\S)_(?:\b|$)", NOFLAG), desugared="</i u>"),
    _MarkdownRegex(regex=re_compile(r"\*(?=\S)", NOFLAG), desugared="<i s>"),
    _MarkdownRegex(regex=re_compile(r"(?<=\S)\*", NOFLAG), desugared="</i s>"),
    _MarkdownRegex(
        regex=re_compile(r"\[(.*?(?<!\\))\]\(.*?(?<!\\)\)", DOTALL),
        desugared=R"<a>\1</a>",
    ),
)
_HTML_TAG_REGEX = re_compile(r"<([^>]+)>", NOFLAG)


def text(text: str):
    """Wrap plain `text` into the standard section format used by generators."""
    return Unit(text).map(strip_lines).map(_SECTION_TEXT_FORMAT.format).counit()


TEXT = text


def quote(text: str, prefix: str = "> "):
    """Return `text` formatted as a quote block with given `prefix`."""
    return Unit(text).map(partial(affix_lines, prefix=prefix)).counit()


def quotette(text: str, prefix: str = "> "):
    """Return `text` quoted and formatted using the section wrapper."""
    return Unit(text).map(partial(quote, prefix=prefix)).map(TEXT).counit()


def quote_text(code: TextCode, /, *, tag: str = Tag.TEXT, line_prefix: str = "> "):
    """Convert `code` into quoted plain text using the given `tag`."""
    return (
        Unit(code)
        .map(partial(code_to_str, tag=tag))
        .map(partial(quotette, prefix=line_prefix))
        .counit()
    )


def cloze_text(
    code: TextCode,
    /,
    *,
    tag: str = Tag.TEXT,
    sep_tag: str = Tag.CLOZE_SEPARATOR,
    token: tuple[str, str] = CONFIG.cloze_token,
    line_prefix: str = "> ",
    separator: str = "\n\n",
    states: Iterable[FlashcardStateGroup],
):
    """Convert cloze-tagged `code` into quoted text containing flashcards.

    `states` provides an iterator of `FlashcardStateGroup` instances used
    to attach state information to generated flashcards.
    """
    return (
        Unit(code)
        .map(partial(separate_code_by_tag, tag=sep_tag))
        .map(lambda codes: map(partial(code_to_str, tag=tag), codes))
        .map(partial(cloze_texts, token=token))
        .map(partial(attach_flashcard_states, states=states))
        .map(lambda groups: map(str, groups))
        .map(lambda strs: map(partial(quote, prefix=line_prefix), strs))
        .map(separator.join)
        .map(text)
        .counit()
    )


def tagged_filter_sep(
    code: TextCode,
    /,
    *,
    tag: str,
    sep_tag: str | None = None,
    empty: bool = False,
):
    """Return textual fragments of `code` filtered by `tag` and separators.

    If `sep_tag` is provided, code is first split by that tag; otherwise all
    blocks are considered. When `empty=False` empty fragments are removed.
    """
    if sep_tag is None:
        unit = Unit(code).map(partial(code_to_strs, tag=tag))
    else:
        unit = (
            Unit(code)
            .map(partial(separate_code_by_tag, tag=sep_tag))
            .map(lambda codes: map(partial(code_to_str, tag=tag), codes))
        )
    if not empty:
        unit = unit.map(lambda strs: filter(lambda x: len(x) > 0, strs))
    return unit.counit()


def memorize(
    code: TextCode,
    /,
    *,
    func: Callable[[Iterable[str]], Iterable[FlashcardGroup]],
    states: Iterable[FlashcardStateGroup],
    tag: str = Tag.MEMORIZE,
    sep_tag: str | None = None,
    empty: bool = False,
    ordered: bool = False,
):
    """Apply a memorization function `func` to `code` and format the result.

    The `func` returns an iterator of flashcard groups which are paired with
    `states` and rendered as text.
    """
    return (
        Unit(code)
        .map(partial(tagged_filter_sep, tag=tag, sep_tag=sep_tag, empty=empty))
        .map(func)
        .map(partial(attach_flashcard_states, states=states))
        .map(partial(listify_flashcards, ordered=ordered))
        .map(text)
        .counit()
    )


def memorize_two_sided(
    code: TextCode,
    /,
    *,
    offsets: Callable[[int], int | None] | Sequence[int] | int = 1,
    hinter: Callable[[int, str], tuple[str, str]] = constant(("", "")),
    reversible: bool = True,
    **kwargs: Any,
):
    """Convenience wrapper to create two-sided flashcards from `code`."""
    return memorize(
        code,
        func=partial(
            memorize_two_sided0,
            offsets=(
                constant(offsets)
                if isinstance(offsets, int)
                else offsets.__getitem__
                if isinstance(offsets, Sequence)
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
    hinted: Callable[[int], bool] | Sequence[bool] | bool = True,
    sanitizer: Callable[[str], str] = identity,
    reversible: bool = True,
    **kwargs: Any,
):
    """Create linked-sequence flashcards using `memorize` with a hinter."""
    return memorize(
        code,
        func=partial(
            memorize_linked_seq0,
            reversible=reversible,
            hinter=punctuation_hinter(
                (
                    constant(hinted)
                    if isinstance(hinted, bool)
                    else hinted.__getitem__
                    if isinstance(hinted, Sequence)
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
    indices: Callable[[int], int | None] | Sequence[int | None] | int = 1,
    reversible: bool = True,
    **kwargs: Any,
):
    """Create index-based flashcards from `code` using a sequence of indices."""
    return memorize(
        code,
        func=partial(
            memorize_indexed_seq0,
            indices=(
                indices.__add__
                if isinstance(indices, int)
                else indices.__getitem__
                if isinstance(indices, Sequence)
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
    states: Iterable[FlashcardStateGroup],
    tags: str | tuple[str, str] = Tag.SEMANTICS,
    sep_tags: tuple[str | None, str | None] | str | None = None,
    empty: tuple[bool, bool] | bool = False,
    reversible: bool = False,
    ordered: bool = False,
):
    """Create semantic mapping flashcards from two `TextCode` inputs.

    `code` provides the prompt text and `sem` the semantic values. The
    resulting flashcards are paired with `states` and rendered as text.
    """
    if not isinstance(tags, tuple):
        tags = (tags, tags)
    if not isinstance(sep_tags, tuple):
        sep_tags = (sep_tags, sep_tags)
    if not isinstance(empty, tuple):
        empty = (empty, empty)
    return (
        Unit((code, sem))
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
        .map(partial(semantics_seq_map0, reversible=reversible))
        .map(partial(attach_flashcard_states, states=states))
        .map(partial(listify_flashcards, ordered=ordered))
        .map(text)
        .counit()
    )


def markdown_sanitizer(text: str):
    """Sanitize `text` by desugaring limited inline markdown and removing tags."""

    def get_and_del_tags(text: str):
        tags = set[str]()
        matches = list[Match[str]]()

        stack = list[Match[str]]()
        match: Match[str]
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
        matches.sort(key=Match[str].start)

        def ret_gen() -> Iterator[str]:
            prev: int = 0
            match: Match[str]
            for match in matches:
                yield text[prev : match.start()]
                prev = match.end()
            yield text[prev:]

        return ("".join(ret_gen()), frozenset(tags))

    text, tags = get_and_del_tags(text)
    distinguisher = "\0" * (len(max(tags, key=len, default="")) + 1)
    for regex in _MARKDOWN_REGEXES:
        text = regex.regex.sub(
            _HTML_TAG_REGEX.sub(
                lambda m: (
                    f"<{m[1][:-1]}{distinguisher}/>"
                    if m[1].endswith("/")
                    else f"<{m[1]}{distinguisher}>"
                ),
                regex.desugared,
            ),
            text,
        )
    text, _ = get_and_del_tags(text)
    return unescape(text)


def seq_to_code(
    seq: Sequence[str],
    /,
    *,
    index: int = 1,
    prefix: str = "",
    suffix: str = "",
    escape: bool = False,
):
    """Convert a sequence of strings into a `TextCode` list representation."""

    def gen_code():
        yield prefix
        newline = ""
        for idx, str_ in enumerate(seq):
            yield f"{{{Tag.TEXT}:{newline}{index + idx}. }}{TextCode.escape(str_, block=True) if escape else str_}"
            newline = "\n"
        yield suffix

    return TextCode.compile("".join(gen_code()))


def map_to_code(
    map: Mapping[str, str],
    /,
    *,
    name: str = "",
    token: tuple[str, str] = CONFIG.cloze_token,
    name_cloze: bool = False,
    key_cloze: bool = False,
    value_cloze: bool = True,
):
    """Convert a mapping into a `TextCode` list representation.

    Each mapping entry becomes a list item of "key: value". Optional
    `name` may be rendered as a heading, and `name_cloze`, `key_cloze`,
    `value_cloze` control whether to wrap components in cloze tokens.
    """
    token = (TextCode.escape(token[0]), TextCode.escape(token[1]))
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

    return TextCode.compile("".join(gen_code()))


def maps_to_code(
    maps: Mapping[str, Mapping[str, str]],
    /,
    *,
    sep_tag: str = Tag.CLOZE_SEPARATOR,
    **kwargs: Any,
):
    """Combine multiple mappings into a single `TextCode` with sections.

    Each mapping is converted via `map_to_code` and joined using `sep_tag`.
    """

    def codegen():
        for key, value in maps.items():
            yield str(map_to_code(value, name=key, **kwargs))

    return TextCode.compile(f"{{{TextCode.escape(sep_tag)}:}}".join(codegen()))


def rows_to_table(
    rows: Iterable[_T],
    /,
    *,
    names: Iterable[str | tuple[str, Literal["default", "left", "right", "center"]]],
    values: Callable[[_T], Iterable[Any]],
    escape: bool = True,
    use_compiled_len: bool = False,  # compile TextCode and use its length
    use_visible_len: bool = False,  # use advanced visible width counting (wcwidth, CJK, diacritics)
):
    """Render `rows` as a Markdown table using provided `names` and `values`.

    `names` supplies headers and optional alignments; `values` extracts
    cell values for each row. Options control escaping and width calculations.
    """
    if escape:

        def escaper(var: str):
            return var.replace("|", "\\|")

    else:
        escaper = identity

    # Prepare headers as a lazily-cached sequence of (escaped_name, align, visible_len) tuples
    def _header_gen():
        for name in names:
            if isinstance(name, str):
                hs, align = escaper(str(name)), "default"
            else:
                hs, align = escaper(str(name[0])), name[1]
            hv = _compute_display_length(hs, use_compiled_len, use_visible_len)
            yield (hs, align, hv)

    headers = IteratorSequence(_header_gen())

    # Create a lazily-cached sequence of processed rows (escaped strings with visible lengths)
    def _rows_gen():
        for row in rows:

            def _cells():
                for c in values(row):
                    cs = escaper(str(c))
                    cv = _compute_display_length(cs, use_compiled_len, use_visible_len)
                    yield (cs, cv)

            yield IteratorSequence(_cells())

    rows_seq = IteratorSequence(_rows_gen())

    # Compute column widths based on stored visible lengths (no further compilation)
    widths = tuple(
        max(
            3,
            max(
                chain(
                    (hv,),
                    (r[i][1] if i < len(r) else 0 for r in rows_seq),
                )
            ),
        )
        for i, (_, _, hv) in enumerate(headers)
    )

    def make_align_token(align: str, width: int) -> str:
        # Build an alignment token with length at least 3 and equal to the column width
        target_len = max(3, width)
        if align == "left":
            # ":---"
            return f":{'-' * (target_len - 1)}"
        if align == "right":
            return f"{'-' * (target_len - 1)}:"
        if align == "center":
            return f":{'-' * (target_len - 2)}:"
        # default
        return f"{'-' * target_len}"

    # Helper: pad a string to a visible width (use precomputed visible length)
    def pad_visible(s: str, vis: int, width: int) -> str:
        if vis >= width:
            return s
        return s + (" " * (width - vis))

    # Build lines with padded cells using zip for clarity (no explicit index variable)
    header_line = f"| {' | '.join(pad_visible(h, hv, w) for (h, _, hv), w in zip(headers, widths))} |"
    align_line = f"| {' | '.join(make_align_token(a, w) for (_, a, _), w in zip(headers, widths))} |"
    # Assemble rows by reading the cached rows from rows_seq (padding/truncating as needed)
    row_lines = (
        f"| {' | '.join(pad_visible((r[i][0] if i < len(r) else ''), (r[i][1] if i < len(r) else 0), w) for i, w in enumerate(widths))} |"
        for r in rows_seq
    )

    return "\n".join(chain((header_line, align_line), row_lines))


def two_columns_to_code(
    rows: Iterable[_T],
    /,
    *,
    left: Callable[[_T], str],
    right: Callable[[_T], str],
):
    """Compile two-column rows into a `TextCode` combining left and right values.

    Each row yields `left(row)` and `right(row)` which are concatenated into
    a compiled `TextCode` string.
    """
    return TextCode.compile(
        "{}".join(
            item if item else "{:}"
            for item in chain.from_iterable((left(row), right(row)) for row in rows)
        )
    )


def _visible_display_width(text: str) -> int:
    """Return number of terminal columns required to display `text`.

    Prefer `wcwidth.wcswidth` when available for correct handling of CJK and
    combining marks; otherwise fall back to the simple length of the
    normalized string. Installing `wcwidth` is recommended for accurate
    visible widths.
    """
    s = normalize("NFC", text)
    if wcswidth is not None and (w := wcswidth(s)) >= 0:
        return w
    return len(s)


def _compute_display_length(s: str, use_compiled: bool, use_visible: bool) -> int:
    """Compute the display length for string ``s`` according to flags.

    The returned value is the number of columns ``s`` will occupy when
    rendered. Behavior depends on the flags passed:

    - If ``use_compiled`` is True, the function first attempts to compile
      ``s`` as a ``TextCode`` fragment and convert it to a string via
      ``code_to_str``. If compilation raises ``ValueError``, the original ``s``
      is used unchanged.
    - If ``use_visible`` is True, the function measures the *visible*
      display width using :func:`_visible_display_width`. That helper
      normalizes text to NFC and prefers ``wcwidth.wcswidth`` when
      available, which gives correct column counts for CJK characters
      and combining diacritics.
    - If ``use_visible`` is False, the function returns ``len(s)`` of the
      selected string (compiled or raw).

    Returns:
        int: number of display columns (or ``len`` of the string when
        ``use_visible`` is False).
    """
    if use_compiled:
        try:
            s = code_to_str(TextCode.compile(s))
        except ValueError:
            pass
    return _visible_display_width(s) if use_visible else len(s)
