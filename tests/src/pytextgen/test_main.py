"""Tests for top-level CLI parsers and `__main__` dispatch.

Covers:
- `pytextgen.main.parser` produces subcommands and version handling
- `pytextgen.__main__` calls runnify with the correct arguments.
"""

from argparse import ArgumentParser

import pytest

from pytextgen import __main__ as pkg_main
from pytextgen import main as top_main

"""Public symbols exported by this module (none)."""
__all__ = ()


def test_top_level_parser_has_subcommands_and_version():
    """Top-level parser exposes expected subcommands and version option."""
    p = top_main.parser()
    # parser must be an ArgumentParser and require a subcommand
    assert isinstance(p, ArgumentParser)

    # verify that 'clear' and 'generate' can be parsed (invoke will be set)
    ns = p.parse_args(["clear", "./does/not/matter"])
    assert hasattr(ns, "invoke")

    ns2 = p.parse_args(["generate", "./does/not/matter"])
    assert hasattr(ns2, "invoke")


def test_top_level_parser_version_flag_exits_cleanly() -> None:
    """`--version` should trigger argparse version action and exit with code 0."""
    with pytest.raises(SystemExit) as excinfo:
        top_main.parser().parse_args(["--version"])
    assert excinfo.value.code == 0


def test_top_level_parser_uses_parent_factory() -> None:
    """Supplying a parent factory should delegate parser construction to it."""
    seen: list[tuple[str | None, str | None, bool, bool, bool]] = []

    def parent(
        *,
        prog: str | None = None,
        description: str | None = None,
        add_help: bool = True,
        allow_abbrev: bool = True,
        exit_on_error: bool = True,
    ) -> ArgumentParser:
        """Capture parser kwargs and construct a real ``ArgumentParser``."""
        seen.append((prog, description, add_help, allow_abbrev, exit_on_error))
        return ArgumentParser(
            prog=prog,
            description=description,
            add_help=add_help,
            allow_abbrev=allow_abbrev,
            exit_on_error=exit_on_error,
        )

    parser = top_main.parser(parent=parent)
    assert isinstance(parser, ArgumentParser)
    assert seen, "Expected parent parser factory to be called"
    assert seen[0][3] is False
    assert seen[0][4] is False


def test___main___calls_runnify_with_correct_arguments(monkeypatch: pytest.MonkeyPatch):
    """`__main__` calls runnify with main and backend_options use_uvloop True."""
    runnify_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def capture_runnify(*args: object, **kwargs: object) -> object:
        """Record runnify arguments and return a no-op callable so __main__ completes."""
        runnify_calls.append((args, dict(kwargs)))

        def noop(*_args: object, **_kwargs: object) -> None:
            """No-op so runnify(...)() does nothing."""
            return None

        return noop

    monkeypatch.setattr(pkg_main, "runnify", capture_runnify)
    pkg_main.__main__()

    assert len(runnify_calls) == 1
    args, kwargs = runnify_calls[0]
    assert len(args) == 1
    assert args[0] is pkg_main.main
    assert kwargs.get("backend_options") == {"use_uvloop": True}
