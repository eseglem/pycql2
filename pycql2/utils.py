from typing import Sequence

QUOTE = "'"
QUOTE_QUOTE = "''"
BACKSLASH_QUOTE = r"\'"


def _make_char_literal(characters: str) -> str:
    """Converts string to a CQL2 Character Literal.

    Adds single quotes `'` around string.
    Escapes any single quotes with backslash `\'`.
    """
    return f"'{characters.replace(QUOTE, BACKSLASH_QUOTE)}'"


def _clean_char_literal(characters: str) -> str:
    """Cleans CQL2 Character Literal.

    Removes outer single quotes `'`.
    Removes escaping from single quotes `''` or `\'`

    Based on the grammar, we know the first and last characters are single quotes `'`.
    """
    return characters[1:-1].replace(QUOTE_QUOTE, QUOTE).replace(BACKSLASH_QUOTE, QUOTE)


def _join_list(items: Sequence, sep: str) -> str:
    """Join string of each item with sep."""
    return sep.join(str(item) for item in items)
