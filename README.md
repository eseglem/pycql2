## Overview

Pydantic models and lark parser for OGC CQL2. As the the specification is still in draft format, changes may be made and cause this to become incorrect.

Representations are not perfectly transitive. In cql2-json and cql2-text there are slightly different ways to represent everything. Internally everything is represented as cql2-json and some details of the cql2-text are no longer needed after being parsed. So, it is impossible to guarantee a round trip operation: `cql2-text -> cql2-json -> cql2-text` will result in an identical string. The meaning will not be changed but the representation might.

When parsing cql2-text to cql2-json.
- Due to how the JSON representation works, `NOT` is pulled out in front of comparison predicates.
    - `... NOT LIKE ...` becomes `NOT ... LIKE ...`
    - `... NOT BETWEEN ...` becomes `NOT ... BETWEEN ...`
    - `... NOT IN ...` become `NOT ... IN ...`
    - `... IS NOT NULL` becomes `NOT ... IS NULL`
- Negative arithmetic operands become a multiply by -1: `{"op": "*", "params": [-1, <arithmetic_operand>]}`

The cql2-text output from the pydantic models is opinionated and explicit. These choices have been made to keep the logic simple while ensuring the correctness of the output.
- All property names are double quoted `"`.
- Parenthesis `()` are placed around all comparison and arithmetic operations.
    - This means that many outputs include a set of parentheses around the whole string. While this is not ideal, it is also not incorrect. When more tests are in place, they can be used to determine if a safe and easy way exists to remove them.
- Timestamps always contain decimal seconds out to 6 decimal places even when 0: `.000000`. It uses `strftime` with `%f` currently. Logic may be added later to adjust this.
- Floats ending in `.0` will include the `.0` in the text. Where other libraries such as `shapely` will not include them in WKT.

The cql2-text spec was not strictly followed for WKT. Some tweaks were made to increase it is compatible with `geojson-pydantic`, as well as accept the WKT output.
- Added optional `Z` to each geometry. It doesn't enforce 2d / 3d, just allows the character to be there.
- LineString coordinates require a minimum of 2 coordinates.
- Added 'Linear Ring' for use in Polygons with a minimum of 4 coordinates. It doesn't enforce the ring being closed, just that it has enough coordinates to be one.
- Moved BBOX so it cannot be included in GeometryCollection.
- Moved GeometryCollection to not allow nesting, until support is added to `geojson-pydantic`.

There are a few things which **may** be issues with the spec but have not been fully addressed yet.
- (Partially addressed) `spatial_literal` includes `geometry_collection` and `bbox`, and `geometry_collection` allows for all `spatial_literal` within it. But `bbox` does not seem to be a part of WKT. And at least within GeoJSON, nested `GeometryCollection` "SHOULD be avoided". This would mean the `cql2-text -> cql2-json` conversion would break where `geojson-pydantic` doesn't accept these cases.
- The spec does not allow for `EMPTY` geometries.

---
## Tests

The tests have been created to exercise various parts of the parsers, and are not meant to serve as realistic examples. Parts like geometries may not make sense but are valid per the specs.

Each file in `tests/data/json/` is a standalone cql2-json example. There will be at least one corresponding file in `tests/data/text` which is a cql2-text equivalent. These corresponding examples should always convert back and forth identically. Since there are multiple ways to write the same thing in cql2-text there may be additional numbered alternative examples like `-alt01`. These will all parse to the same json, which in turn will output the main text example.

While 100% of the lines of code are covered, more complex examples with more nested logic will be added in the future. As well as more variety to various inputs, the current examples are mostly PropertyRef and numbers. Such as:
- More complex identifiers with `_`, `.`, `:`, and non ascii letters.
- Character literals with escaped quote.
- Deeply nested logic.
- Each type of `scalar_expression` on each side of a `binary_comparison_predicate`, etc.

## Hypothesis

Support has been added for `Hypothesis` for cql2-text. The grammar is quite complex so this can be very slow, but a few bugs have been found with it. Strategies had to be tweaked to handle date / datetime as the grammar allows for dates like `0000-00-00` but python will not parse them. Additionally, a custom strategy was added for polygons, since the grammar has no ability to convey closing a polygon.

In addition to this, `HypoFuzz` was used to run coverage based testing. It ran 33,000 different tests including 22,961 of them without finding a new branches in the code to cover. This seems to indicate the `cql2-text -> cql2-json` transformation has been fairly thoroughly tested.

Support will be added for cql2-json later. There are additional custom strategies which will be necessary.

---

Writing this parser has resulted in feedback and contributions to the [ogcapi-features](https://github.com/opengeospatial/ogcapi-features) CQL2 spec:
- Reported issue with Alpha and Symbols (fixed): https://github.com/opengeospatial/ogcapi-features/issues/787
- Submit PR for minor inconsistencies between schema formats (pending): https://github.com/opengeospatial/ogcapi-features/pull/794
- Added notes to Updating examples ticket and offered these tests back: https://github.com/opengeospatial/ogcapi-features/issues/783
- Reported observations about WKT grammar (pending): https://github.com/opengeospatial/ogcapi-features/issues/800
