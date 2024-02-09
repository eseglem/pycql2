from pathlib import Path

import pytest
from lark import UnexpectedCharacters
from pydantic import ValidationError

from pycql2.cql2_pydantic import BooleanExpression
from pycql2.cql2_transformer import parser, transformer

JSON_DIR = Path("tests/data/json")
TEXT_DIR = Path("tests/data/text")
json_files = sorted(_.name for _ in JSON_DIR.glob("*.json"))
text_files = sorted(_.name for _ in TEXT_DIR.glob("*.txt"))

BAD_JSON_DIR = Path("tests/bad_data/json")
BAD_TEXT_DIR = Path("tests/bad_data/text")
bad_json_files = sorted(_.name for _ in BAD_JSON_DIR.glob("*.json"))
bad_text_files = sorted(_.name for _ in BAD_TEXT_DIR.glob("*.txt"))


@pytest.mark.parametrize("file_name", json_files)
def test_parse_json(file_name: str) -> None:
    """Test that the pydantic model can parse the json."""

    json_file = JSON_DIR / file_name
    _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("file_name", text_files)
def test_parse_text(file_name: str) -> None:
    """Test that the parser can parse the text."""

    text_file = TEXT_DIR / file_name
    _ = parser.parse(text_file.read_text())


@pytest.mark.parametrize("file_name", bad_json_files)
def test_parse_bad_json(file_name: str) -> None:
    """Test that the pydantic model does not parse the bad json."""

    json_file = BAD_JSON_DIR / file_name
    with pytest.raises(ValidationError):
        _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("file_name", bad_text_files)
def test_parse_bad_text(file_name: str) -> None:
    """Test that the parser does not parse the bad text."""

    text_file = BAD_TEXT_DIR / file_name
    with pytest.raises(UnexpectedCharacters):
        _ = parser.parse(text_file.read_text())


@pytest.mark.parametrize("file_name", json_files)
def test_json_to_text(file_name: str) -> None:
    """Test that the pydantic model outputs the correct text representation."""

    json_file = JSON_DIR / file_name
    # Load the json data
    model = BooleanExpression.model_validate_json(json_file.read_text())
    # Load the expected text data
    text_file = TEXT_DIR / (json_file.stem + ".txt")
    expected = text_file.read_text().strip()
    # Compare the two
    assert str(model) == expected


@pytest.mark.parametrize("file_name", text_files)
def test_text_to_json(file_name: str) -> None:
    """Test that the parser outputs the correct json representation."""

    text_file = TEXT_DIR / file_name
    # Load the text data
    tree = parser.parse(text_file.read_text())
    output = transformer.transform(tree)
    # Some text files are equivalent to the same json file. These contain
    # "-alt" in the file names. We split on the "-" to get the base name.
    json_file = JSON_DIR / (text_file.stem.split("-")[0] + ".json")
    # Load the expected json data
    expected = BooleanExpression.model_validate_json(json_file.read_text())
    # Compare the two
    assert output == expected
