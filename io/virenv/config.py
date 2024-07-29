from dataclasses import dataclass as _dc, field as _field
from typing import (
    Callable as _Call,
    ClassVar as _ClsVar,
    Mapping as _Map,
    MutableMapping as _MMap,
    Self as _Self,
    final as _fin,
)


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
    cloze_token: tuple[str, str] = ("{{", "}}")
    flashcard_separators: _MMap[FlashcardSeparatorType, str] = _field(
        default_factory=lambda: {
            FlashcardSeparatorType.parse(""): "::",
            FlashcardSeparatorType.parse("r"): ":::",
            FlashcardSeparatorType.parse("m"): "??",
            FlashcardSeparatorType.parse("rm"): "???",
        },
    )


CONFIG = Configuration()
