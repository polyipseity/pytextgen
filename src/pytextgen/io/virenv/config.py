"""Configuration defaults for the virtual environment helpers.

Provides default tokens and flashcard separator settings used by the
`virenv` IO helpers.
"""

from dataclasses import dataclass, field
from typing import (
    Callable,
    ClassVar,
    Mapping,
    MutableMapping,
    Self,
    final,
)

__all__ = ("FlashcardSeparatorType", "Configuration", "CONFIG")


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
class FlashcardSeparatorType:
    """Representation of flashcard separator options.

    Instances indicate whether a separator is `reversible` and/or
    `multiline`; parsing is provided via :meth:`parse`.
    """

    OPTIONS: ClassVar[Mapping[str, Callable[[Self, bool], None]]] = {
        "r": lambda self, value: object.__setattr__(self, "reversible", value),
        "m": lambda self, value: object.__setattr__(self, "multiline", value),
    }

    reversible: bool
    multiline: bool

    @classmethod
    def parse(cls, options: str | Self):
        if not isinstance(options, str):
            return options
        self = cls(reversible=False, multiline=False)
        value = True
        for char in options:
            if char == "-":
                if not value:
                    raise ValueError(f"Invalid options: {options}")
                value = False
                continue
            try:
                cls.OPTIONS[char](self, value)
            except KeyError as exc:
                raise ValueError(f"Invalid option '{char}': {options}") from exc
            value = True
        if not value:
            raise ValueError(f"Incomplete options: {options}")
        return self


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
class Configuration:
    """Configuration values for the virtual environment helpers.

    Provides defaults for cloze token handling and flashcard separators.
    """

    cloze_token: tuple[str, str] = (R"{@{", R"}@}")
    flashcard_separators: MutableMapping[FlashcardSeparatorType, str] = field(
        default_factory=lambda: {
            FlashcardSeparatorType.parse(""): R":@:",
            FlashcardSeparatorType.parse("r"): R"::@::",
            FlashcardSeparatorType.parse("m"): R"?@?",
            FlashcardSeparatorType.parse("rm"): R"??@??",
        },
    )


CONFIG = Configuration()
