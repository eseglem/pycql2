import json
import os

import pytest
from lark import UnexpectedCharacters
from pydantic import ValidationError

from pycql2.cql2_pydantic import BooleanExpression
from pycql2.cql2_transformer import parser, transformer

JSON_DIR = "tests/data/json"
TEXT_DIR = "tests/data/text"
json_files = os.listdir(JSON_DIR)
text_files = os.listdir(TEXT_DIR)

BAD_JSON_DIR = "tests/bad_data/json"
BAD_TEXT_DIR = "tests/bad_data/text"
bad_json_files = os.listdir(BAD_JSON_DIR)
bad_text_files = os.listdir(BAD_TEXT_DIR)


@pytest.mark.parametrize("json_file", json_files)
def test_parse_json(json_file: str) -> None:
    # Simply test that the pydantic model can parse the json
    with open(os.path.join(JSON_DIR, json_file)) as inf:
        json_data = json.load(inf)
    _ = BooleanExpression.parse_obj(json_data)


@pytest.mark.parametrize("text_file", text_files)
def test_parse_text(text_file: str) -> None:
    # Simply test that the parser can parse the text
    with open(os.path.join(TEXT_DIR, text_file)) as inf:
        text_data = inf.read()
    _ = parser.parse(text_data)


@pytest.mark.parametrize("json_file", bad_json_files)
def test_parse_bad_json(json_file: str) -> None:
    # Simply test that the pydantic model can parse the json
    with open(os.path.join(BAD_JSON_DIR, json_file)) as inf:
        json_data = json.load(inf)
    with pytest.raises(ValidationError):
        _ = BooleanExpression.parse_obj(json_data)


@pytest.mark.parametrize("text_file", bad_text_files)
def test_parse_bad_text(text_file: str) -> None:
    # Simply test that the parser can parse the text
    with open(os.path.join(BAD_TEXT_DIR, text_file)) as inf:
        text_data = inf.read()
    with pytest.raises(UnexpectedCharacters):
        _ = parser.parse(text_data)


@pytest.mark.parametrize("json_file", json_files)
def test_json_to_text(json_file: str) -> None:
    # Test that the pydantic model outputs the correct text representation

    # Load the json data
    with open(os.path.join(JSON_DIR, json_file)) as inf:
        json_data = json.load(inf)
    model = BooleanExpression.parse_obj(json_data)
    # Load the expected text data
    text_file = json_file.replace(".json", ".txt")
    with open(os.path.join(TEXT_DIR, text_file)) as inf:
        expected = inf.read().strip()
    # Compare the two
    assert str(model) == expected


@pytest.mark.parametrize("text_file", text_files)
def test_text_to_json(text_file: str) -> None:
    # Test that the parser outputs the correct json representation

    # Load the text data
    with open(os.path.join(TEXT_DIR, text_file)) as inf:
        text_data = inf.read()
    model = parser.parse(text_data)

    # Load the expected json data
    json_file = text_file.replace(".txt", ".json")
    # Some text files have an "alt" suffix, which means that they are
    # equivalent to the same json file.  In this case, we want to load
    # the json file without the "alt" suffix.
    if "alt" in json_file:
        json_file = json_file.split("-")[0] + ".json"
    with open(os.path.join(JSON_DIR, json_file)) as inf:
        json_data = json.load(inf)
    expected = BooleanExpression.parse_obj(json_data)
    # Compare the two. We use __root__ because the json data is wrapped
    # by the BooleanExpression model.
    assert transformer.transform(model) == expected.__root__
