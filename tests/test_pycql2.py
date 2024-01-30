from pathlib import Path

import pytest
from lark import UnexpectedCharacters
from pydantic import ValidationError

from pycql2.cql2_pydantic import BooleanExpression
from pycql2.cql2_transformer import parser, transformer

JSON_DIR = Path("tests/data/json")
TEXT_DIR = Path("tests/data/text")
json_files = list(JSON_DIR.glob("*.json"))
text_files = list(TEXT_DIR.glob("*.txt"))

BAD_JSON_DIR = Path("tests/bad_data/json")
BAD_TEXT_DIR = Path("tests/bad_data/text")
bad_json_files = list(BAD_JSON_DIR.glob("*.json"))
bad_text_files = list(BAD_TEXT_DIR.glob("*.txt"))


@pytest.mark.parametrize("json_file", json_files)
def test_parse_json(json_file: Path) -> None:
    """Test that the pydantic model can parse the json."""

    _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("text_file", text_files)
def test_parse_text(text_file: Path) -> None:
    """Test that the parser can parse the text."""

    _ = parser.parse(text_file.read_text())


@pytest.mark.parametrize("json_file", bad_json_files)
def test_parse_bad_json(json_file: Path) -> None:
    """Test that the pydantic model does not parse the bad json."""

    with pytest.raises(ValidationError):
        _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("text_file", bad_text_files)
def test_parse_bad_text(text_file: Path) -> None:
    """Test that the parser does not parse the bad text."""

    with pytest.raises(UnexpectedCharacters):
        _ = parser.parse(text_file.read_text())


@pytest.mark.parametrize("json_file", json_files)
def test_json_to_text(json_file: Path) -> None:
    """Test that the pydantic model outputs the correct text representation."""

    # Load the json data
    model = BooleanExpression.model_validate_json(json_file.read_text())
    # Load the expected text data
    text_file = TEXT_DIR / (json_file.stem + ".txt")
    expected = text_file.read_text().strip()
    # Compare the two
    assert str(model) == expected


@pytest.mark.parametrize("text_file", text_files)
def test_text_to_json(text_file: Path) -> None:
    """Test that the parser outputs the correct json representation."""

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
