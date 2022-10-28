import dataclasses as _dataclasses
import functools as _functools
import re as _re
import typing as _typing

from .. import util as _util
from . import flashcard as _flashcard
from . import misc as _misc
from . import text_code as _text_code

_section_text_format: str = '\n\n{}\n'


@_typing.final
@_dataclasses.dataclass(init=True,
                        repr=True,
                        eq=True,
                        order=False,
                        unsafe_hash=False,
                        frozen=True,
                        match_args=True,
                        kw_only=True,
                        slots=True,)
class _MarkdownRegex:
    regex: _re.Pattern[str]
    desugared: str


_markdown_regexes: _typing.Sequence[_MarkdownRegex] = (
    _MarkdownRegex(regex=_re.compile(r'(?:\b|^)__(?=\S)', flags=0),
                   desugared='<b u>'),
    _MarkdownRegex(regex=_re.compile(r'(?<=\S)__(?:\b|$)', flags=0),
                   desugared='</b u>'),
    _MarkdownRegex(regex=_re.compile(r'\*\*(?=\S)', flags=0),
                   desugared='<b s>'),
    _MarkdownRegex(regex=_re.compile(r'(?<=\S)\*\*', flags=0),
                   desugared='</b s>'),
    _MarkdownRegex(regex=_re.compile(r'(?:\b|^)_(?=\S)', flags=0),
                   desugared='<i u>'),
    _MarkdownRegex(regex=_re.compile(r'(?<=\S)_(?:\b|$)', flags=0),
                   desugared='</i u>'),
    _MarkdownRegex(regex=_re.compile(r'\*(?=\S)', flags=0),
                   desugared='<i s>'),
    _MarkdownRegex(regex=_re.compile(r'(?<=\S)\*', flags=0),
                   desugared='</i s>'),
)
_html_tag_regex: _re.Pattern[str] = _re.compile(r'<([^>]+)>', flags=0)


def quote_text(code: _text_code.TextCode, /, *,
               tag: _misc.TagStr = _misc.Tag.TEXT,
               ) -> str:
    return (_util.Unit(code)
            .map(_functools.partial(_text_code.code_to_str, tag=tag))
            .map(_functools.partial(_misc.affix_lines, prefix='> '))
            .map(_misc.strip_lines)
            .map(_section_text_format.format)
            .counit())


def memorize_linked_seq(code: _text_code.TextCode, /, *,
                        hinted: _typing.Callable[[
                            int], bool] | _typing.Sequence[bool] | bool = True,
                        states: _typing.Iterable[_util.FlashcardStateGroup],
                        sanitizer: _typing.Callable[[
                            str], str] = _util.identity,
                        reversible: bool = True,
                        ) -> str:
    return (_util.Unit(code)
            .map(_functools.partial(_text_code.code_to_strs, tag=_misc.Tag.MEMORIZE))
            .map(_functools.partial(_flashcard.memorize_linked_seq,
                                    reversible=reversible,
                                    hinter=_flashcard.punctuation_hinter(
                                        (_util.constant(hinted) if isinstance(hinted, bool) else
                                         hinted.__getitem__ if isinstance(hinted, _typing.Sequence) else
                                         hinted),
                                        sanitizer=sanitizer,
                                    )))
            .map(_functools.partial(_flashcard.attach_flashcard_states, states=states))
            .map(_flashcard.listify_flashcards)
            .map(_misc.strip_lines)
            .map(_section_text_format.format)
            .counit())


def memorize_indexed_seq(code: _text_code.TextCode, /, *,
                         indices: _typing.Callable[[
                             int], int | None] | _typing.Sequence[int | None] | int = 1,
                         states: _typing.Iterable[_util.FlashcardStateGroup],
                         reversible: bool = True,
                         ) -> str:
    return (_util.Unit(code)
            .map(_functools.partial(_text_code.code_to_strs, tag=_misc.Tag.MEMORIZE))
            .map(_functools.partial(_flashcard.memorize_indexed_seq,
                                    indices=(indices.__add__ if isinstance(indices, int) else
                                             indices.__getitem__ if isinstance(indices, _typing.Sequence) else
                                             indices),
                                    reversible=reversible,))
            .map(_functools.partial(_flashcard.attach_flashcard_states, states=states))
            .map(_flashcard.listify_flashcards)
            .map(_misc.strip_lines)
            .map(_section_text_format.format)
            .counit())


def semantics_seq_map(text: _text_code.TextCode, sem: _text_code.TextCode, *,
                      states: _typing.Iterable[_util.FlashcardStateGroup],
                      reversible: bool = False,
                      ) -> str:
    return (_util.Unit((text, sem))
            .map(lambda codes: (
                _text_code.code_to_strs(codes[0], tag=_misc.Tag.SEMANTICS),
                _text_code.code_to_strs(codes[1], tag=_misc.Tag.SEMANTICS)
            ))
            .map(lambda strss: zip(*strss, strict=True))
            .map(_functools.partial(_flashcard.semantics_seq_map, reversible=reversible))
            .map(_functools.partial(_flashcard.attach_flashcard_states, states=states))
            .map(_flashcard.listify_flashcards)
            .map(_misc.strip_lines)
            .map(_section_text_format.format)
            .counit())


def markdown_sanitizer(text: str) -> str:
    def get_and_remove_html_tags(text: str) -> tuple[str, _typing.AbstractSet[str]]:
        tags: _typing.MutableSet[str] = set()
        matches: _typing.MutableSequence[_re.Match[str]] = []

        stack: _typing.MutableSequence[_re.Match[str]] = []
        match: _re.Match[str]
        for match in _html_tag_regex.finditer(text):
            tag: str = match[1]
            if tag.startswith('/'):
                tag0: str = tag[1:]
                tags.add(tag0)
                if stack and stack[-1][1] == tag0:
                    matches.extend((stack.pop(), match))
            elif tag.endswith('/'):
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
                yield text[prev:match.start()]
                prev = match.end()
            yield text[prev:]
        return (''.join(ret_gen()), frozenset(tags))

    tags: _typing.AbstractSet[str]
    text, tags = get_and_remove_html_tags(text)
    distingusher: str = (
        '\0' * (len(max(tags, key=len, default='')) + 1))
    md_regex: _MarkdownRegex
    for md_regex in _markdown_regexes:
        suffix: str = ('/>' if md_regex.desugared.endswith('/>') else
                       '>' if md_regex.desugared.endswith('>') else '')
        text = md_regex.regex.sub(f'{md_regex.desugared[:-len(suffix)]}{distingusher}{suffix}',
                                  text)
    text, _ = get_and_remove_html_tags(text)
    return text
