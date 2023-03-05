Working Pydantic models and lark parser for OGC CQL2. As the the specification is still in draft format, changes may be made and cause this to become incorrect.

Representations are not perfectly transitive. In cql2-json and cql2-text there are slightly different ways to represent everything. Internally everything is represented as cql2-json and some details of the cql2-text are no longer needed after being parsed. So, it is impossible to guarantee a round trip operation: `cql2-text -> cql2-json -> cql2-text` will result in an identical string. The meaning will not be changed but the representation might.

When parsing cql2-text to cql2-json.
- Due to how the JSON representation works, `NOT` is pulled out in front of comparison predicates.
    - `... NOT LIKE ...` becomes `NOT ... LIKE ...`
    - `... NOT BETWEEN ...` becomes `NOT ... BETWEEN ...`
    - `... NOT IN ...` become `NOT ... IN ...`
    - `... IS NOT NULL` becomes `NOT ... IS NULL`
- Any integers `1` will become floats `1.0`
- Negative arithmetic operands become a multiply by -1: `{"op": "*", "params": [-1, <arithmetic_operand>]}`

The cql2-text output from the pydantic models is opinionated and explicit. These choices have been made to keep the logic simple while ensuring the correctness of the output.
- All property names are double quoted `"`.
- Parenthesis `()` are placed around all comparison and arithmetic operations.
    - This means that many outputs include a set of parentheses around the whole string. While this is not ideal, it is also not incorrect. Once tests are in place, they can be used to determine if a safe and easy way exists to remove them.
- Timestamps always contain decimal seconds.
- Floats ending in `.0` will include the `.0` in the text. Where other libraries such as `shapely` will not include them in WKT.

---

The tests have been created to exercise various parts of the parsers, and are not meant to serve as realistic examples. Parts like geometries may not make sense but are valid per the specs.

Each file in `tests/data/json/` is a standalone `cql2-json` example. There will be at least one corresponding file in `tests/data/text` which is a `cql2-text` equivalent. These corresponding examples should always convert back and forth identically. Since there are multiple ways to write the same thing in `cql2-text` there may be additional numbered alternative examples like `-alt01`. These will all parse to the same json, which in turn will output the main text example.
