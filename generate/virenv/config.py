# -*- coding: UTF-8 -*-
import dataclasses as _dataclasses
import types as _types
import typing as _typing


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
class FlashcardSeparatorType:
    OPTIONS: _typing.ClassVar[
        _typing.Mapping[str, _typing.Callable[[_typing.Self, bool], None]]
    ] = _types.MappingProxyType(
        {
            "r": lambda self, value: object.__setattr__(self, "reversible", value),
            "m": lambda self, value: object.__setattr__(self, "multiline", value),
        }
    )

    reversible: bool
    multiline: bool

    @classmethod
    def parse(cls, options: str | _typing.Self) -> _typing.Self:
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
class Configuration:
    cloze_token: tuple[str, str] = ("{{", "}}")
    flashcard_separators: _typing.MutableMapping[
        FlashcardSeparatorType, str
    ] = _dataclasses.field(
        default_factory=lambda: {
            FlashcardSeparatorType.parse(""): "::",
            FlashcardSeparatorType.parse("r"): ":::",
            FlashcardSeparatorType.parse("m"): "??",
            FlashcardSeparatorType.parse("rm"): "???",
        },
    )


CONFIG = Configuration()
