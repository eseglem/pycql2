from pathlib import Path
from typing import Final, List

import pytest
from lark import UnexpectedCharacters
from pydantic import ValidationError

from pycql2.cql2_pydantic import BooleanExpression
from pycql2.cql2_transformer import parser, transformer


def find_files(directory: Path, type: str) -> List[Path]:
    """Find all files in the subdirectory with the given extension."""

    # The text files are in the "text" subdirectory but have the extension "txt"
    extension = "txt" if type == "text" else type
    # Find all the file names in the subdirectory with the given extension
    return sorted((directory / type).glob(f"*.{extension}"))


DATA_DIR: Final[Path] = Path("tests/data")
BAD_DATA_DIR: Final[Path] = Path("tests/bad_data")

JSON_FILES: Final[List[Path]] = find_files(DATA_DIR, "json")
TEXT_FILES: Final[List[Path]] = find_files(DATA_DIR, "text")
BAD_JSON_FILES: Final[List[Path]] = find_files(BAD_DATA_DIR, "json")
BAD_TEXT_FILES: Final[List[Path]] = find_files(BAD_DATA_DIR, "text")


def get_matching_text_file(json_file: Path) -> Path:
    """Get the text file that corresponds with the input json file."""
    return json_file.parent.parent / "text" / (json_file.stem + ".txt")


def get_matching_json_file(text_file: Path) -> Path:
    """Get the json file that corresponds with the input text file."""

    # Some text files are equivalent to the same json file. These contain
    # "-alt" in the file names. We split on the "-" to get the base name.
    return text_file.parent.parent / "json" / (text_file.stem.split("-")[0] + ".json")


@pytest.mark.parametrize("json_file", JSON_FILES)
def test_parse_json(json_file: Path) -> None:
    """Test that the pydantic model can parse the json."""
    _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("text_file", TEXT_FILES)
def test_parse_text(text_file: Path) -> None:
    """Test that the parser can parse the text."""
    _ = parser.parse(text_file.read_text())


@pytest.mark.parametrize("json_file", BAD_JSON_FILES)
def test_parse_bad_json(json_file: Path) -> None:
    """Test that the pydantic model does not parse the bad json."""

    with pytest.raises(ValidationError):
        _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("text_file", BAD_TEXT_FILES)
def test_parse_bad_text(text_file: Path) -> None:
    """Test that the parser does not parse the bad text."""

    with pytest.raises(UnexpectedCharacters):
        _ = parser.parse(text_file.read_text())


@pytest.mark.parametrize("json_file", JSON_FILES)
def test_json_to_text(json_file: Path) -> None:
    """Test that the pydantic model outputs the correct text representation."""

    # Load the json data
    model = BooleanExpression.model_validate_json(json_file.read_text())
    # Load the expected text data
    expected = get_matching_text_file(json_file).read_text().strip()
    # Compare the two
    assert str(model) == expected


@pytest.mark.parametrize("text_file", TEXT_FILES)
def test_text_to_json(text_file: Path) -> None:
    """Test that the parser outputs the correct json representation."""

    # Load the text data
    tree = parser.parse(text_file.read_text())
    output = transformer.transform(tree)
    # Load the expected json data
    expected = BooleanExpression.model_validate_json(
        get_matching_json_file(text_file).read_text()
    )
    # Compare the two
    assert output == expected
