import os
from pathlib import Path

import pytest

from pycql2.cql2_pydantic import BooleanExpression
from pycql2.cql2_transformer import parser, transformer

# Default to being checked out in the same parent directory as this repo
DEFAULT_PATH = Path(__file__).resolve().parent.parent.parent / "ogcapi-features"
# Allow for customization via ENV variable
OGCAPI_FEATURES_PATH = Path(
    os.environ.get("OGCAPI_FEATURES_PATH", DEFAULT_PATH)
).resolve()
# The path to the examples within the repo
EXAMPLES_PATH = OGCAPI_FEATURES_PATH / "cql2/standard/schema/examples/"
JSON_PATH = EXAMPLES_PATH / "json"
TEXT_PATH = EXAMPLES_PATH / "text"

# Initialize the lists of files to be empty
json_files: list[str] = []
text_files: list[str] = []

# If the examples path exists, populate the lists of files
if EXAMPLES_PATH.exists():
    json_files = sorted(_.name for _ in JSON_PATH.glob("*.json"))
    text_files = sorted(_.name for _ in TEXT_PATH.glob("*.txt"))


@pytest.mark.parametrize("file_name", json_files)
def test_parse_json(file_name: str) -> None:
    """Test that the pydantic model can parse the json."""

    json_file = JSON_PATH / file_name
    _ = BooleanExpression.model_validate_json(json_file.read_text())


@pytest.mark.parametrize("file_name", text_files)
def test_parse_text(file_name: str) -> None:
    """Test that the parser can parse the text."""

    text_file = TEXT_PATH / file_name
    tree = parser.parse(text_file.read_text())
    _ = transformer.transform(tree)


@pytest.mark.parametrize("file_name", text_files)
def test_text_to_json(file_name: str) -> None:
    """Test that the parser outputs the correct json representation."""

    text_file = TEXT_PATH / file_name
    # Load the text data
    tree = parser.parse(text_file.read_text())
    output = transformer.transform(tree)
    # Some text files are equivalent to the same json file. These contain
    # "-alt" in the file names. We split on the "-" to get the base name.
    json_file = JSON_PATH / (text_file.stem.split("-")[0] + ".json")
    # Load the expected json data
    expected = BooleanExpression.model_validate_json(json_file.read_text())
    # Compare the two
    assert output == expected
