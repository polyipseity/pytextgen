"""Public helpers used for generating text/code and flashcards.

This package intentionally does not re-export symbols from submodules. Callers
should import directly from the submodule that defines the symbol, for
example:

    from pytextgen.io.virenv.gen._text_code import TextCode
    from pytextgen.io.virenv.gen._flashcard import attach_flashcard_states

Keeping a minimal package surface avoids accidental API stabilization and
makes the origin of each symbol explicit.
"""

__all__ = ()
