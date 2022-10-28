import enum as _enum
import re as _re
import regex as _regex
import sys as _sys
import typing as _typing
import unicodedata as _unicodedata

from . import text_code as _text_code

_punctuations: _typing.Collection[str] = tuple(chr(char) for char in range(_sys.maxunicode)
                                               if _unicodedata.category(chr(char)).startswith('P'))
_punctuation_regex: _regex.Pattern[str] = _regex.compile(
    r'(?<={delims})(?<!^(?:{delims})+)(?!$|{delims})'.format(
        delims=r'|'.join(map(_re.escape, _punctuations))),
    flags=_regex.VERSION0
)


@_enum.unique
class Tag(_enum.Enum):
    __slots__: _typing.ClassVar = ()

    COMMON: _typing.ClassVar = ''
    COMMENT: _typing.ClassVar = 'cmt'
    TEXT: _typing.ClassVar = 'text'
    MEMORIZE: _typing.ClassVar = 'mem'
    SEMANTICS: _typing.ClassVar = 'sem'
    CLOZE_SEPARATOR: _typing.ClassVar = 'cloze sep'

    def __str__(self: _typing.Self) -> str:
        return self.value


TagStr: _typing.TypeAlias = Tag | str


def affix_lines(text: str, /, *, prefix: str = '', suffix: str = '') -> str:
    def ret_gen() -> _typing.Iterator[str]:
        newline: str = ''
        for line in text.splitlines():
            yield newline
            yield prefix
            yield line
            yield suffix
            newline = '\n'
    return ''.join(ret_gen())


def strip_lines(text: str, /, *, chars: str | None = None) -> str:
    return '\n'.join(line.strip(chars) for line in text.splitlines())


def split_by_punctuations(text: str) -> _typing.Iterator[str]:
    return _punctuation_regex.splititer(text)


def code_to_strs(code: _text_code.TextCode, /, *,
                 tag: TagStr = Tag.COMMON) -> _typing.Iterator[str]:
    return (block.text for block in code.blocks if block.common or block.tag == str(tag))


def code_to_str(code: _text_code.TextCode, /, *,
                tag: TagStr = Tag.COMMON) -> str:
    return ''.join(code_to_strs(code, tag=tag))


def affix_code(code: _text_code.TextCode, /, *,
               prefix: str = '',
               suffix: str = '',
               ) -> _text_code.TextCode:
    return code.compile(''.join((prefix, str(code), suffix,)))
