from typing import List, Sequence, Tuple

import pytest

from pycql2.cql2_pydantic import _join_list, _make_char_literal
from pycql2.cql2_transformer import _clean_char_literal

# Cases for testing round trip of 'Character Literals' with
# various numbers of single quotes in the strings.

# First value is the Python string
# Second value is CQL2 Character Literal
CHAR_LITERALS: List[Tuple[str, str]] = [
    # None
    ("a", r"'a'"),
    # One
    ("a'b", r"'a\'b'"),
    # Multiple
    ("a'b'c", r"'a\'b\'c'"),
    # Repeated
    ("a''b", r"'a\'\'b'"),
    # Starts with
    ("'a", r"'\'a'"),
    # Ends with
    ("a'", r"'a\''"),
    # Starts with, repeated, ends with
    ("'a''b'", r"'\'a\'\'b\''"),
]


@pytest.mark.parametrize(("input", "expected"), CHAR_LITERALS)
def test_make_char_literal(input: str, expected: str) -> None:
    assert _make_char_literal(input) == expected


@pytest.mark.parametrize(("expected", "input"), CHAR_LITERALS)
def test_clean_char_literal(input: str, expected: str) -> None:
    assert _clean_char_literal(input) == expected


@pytest.mark.parametrize(
    ("items", "sep", "expected"),
    [
        ((True, False), ",", "True,False"),
        ((1, 2, 3), " ", "1 2 3"),
        ((1.0, 2.0, 3.0), ", ", "1.0, 2.0, 3.0"),
        (("a", "b", "c"), "", "abc"),
    ],
)
def test_join_list(items: Sequence, sep: str, expected: str) -> None:
    assert _join_list(items, sep) == expected
