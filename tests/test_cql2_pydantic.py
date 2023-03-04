from pycql2.cql2_pydantic import join_list, make_char_literal


def test_make_char_literal() -> None:
    assert make_char_literal("a") == "'a'"
    assert make_char_literal("a'b") == "'a''b'"
    assert make_char_literal("a''b") == "'a''''b'"


def test_join_list() -> None:
    assert join_list([True, False], ",") == "True,False"
    assert join_list([1, 2, 3], " ") == "1 2 3"
    assert join_list([1.0, 2.0, 3.0], ", ") == "1.0, 2.0, 3.0"
    assert join_list(["a", "b", "c"], "") == "abc"
