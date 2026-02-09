from dataclasses import dataclass as _dc
from dataclasses import field as _field
from typing import (
    Callable as _Call,
)
from typing import (
    ClassVar as _ClsVar,
)
from typing import (
    Mapping as _Map,
)
from typing import (
    MutableMapping as _MMap,
)
from typing import (
    Self as _Self,
)
from typing import (
    final as _fin,
)

__all__ = ("FlashcardSeparatorType", "Configuration", "CONFIG")


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
class FlashcardSeparatorType:
    OPTIONS: _ClsVar[_Map[str, _Call[[_Self, bool], None]]] = {
        "r": lambda self, value: object.__setattr__(self, "reversible", value),
        "m": lambda self, value: object.__setattr__(self, "multiline", value),
    }

    reversible: bool
    multiline: bool

    @classmethod
    def parse(cls, options: str | _Self):
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
class Configuration:
    """Configuration values for the virtual environment helpers.

    Provides defaults for cloze token handling and flashcard separators.
    """

    cloze_token: tuple[str, str] = (R"{@{", R"}@}")
    flashcard_separators: _MMap[FlashcardSeparatorType, str] = _field(
        default_factory=lambda: {
            FlashcardSeparatorType.parse(""): R":@:",
            FlashcardSeparatorType.parse("r"): R"::@::",
            FlashcardSeparatorType.parse("m"): R"?@?",
            FlashcardSeparatorType.parse("rm"): R"??@??",
        },
    )


CONFIG = Configuration()
