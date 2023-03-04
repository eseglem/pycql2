from datetime import date, datetime, timezone
from typing import Any

from geojson_pydantic import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from lark import Lark, Transformer, v_args

from pycql2.cql2_pydantic import (
    Accenti,
    AndOrExpression,
    ArithmeticExpression,
    ArrayPredicate,
    BboxLiteral,
    BinaryComparisonPredicate,
    Casei,
    DateLiteral,
    Function,
    FunctionRef,
    IntervalLiteral,
    IsBetweenPredicate,
    IsInListPredicate,
    IsLikePredicate,
    IsNullPredicate,
    NotExpression,
    PropertyRef,
    SpatialPredicate,
    TemporalPredicate,
    TimestampLiteral,
)


def passthrough(_self, args: Any) -> Any:
    """Pass the arguments up to the next level of the tree.

    This is utilized throughout the Transformer when additional parsing
    is not necessary.
    """
    return args


class Cql2Transformer(Transformer):
    """Transformer that turns parsed cql2-text into cql2-json."""

    # Treat all signed numbers as floats
    SIGNED_NUMBER = float

    @v_args(inline=True)
    def BOOLEAN_LITERAL(self, boolean_literal: str) -> bool:
        # Text is case insensitive, so upper it and compare with "TRUE"
        return boolean_literal.upper() == "TRUE"

    @v_args(inline=True)
    def DOTDOT(self, dotdot: str) -> str:
        # Strip the `'` which aren't used in the json representation
        return dotdot.strip("'")

    # Splitting these apart within the grammar resulted in errors, so we need to
    # introspect on the number of items to determine the function. All continuos
    # blocks of `or` / `and` are grouped together into single json operation.

    @v_args(inline=True)
    def boolean_expression(self, *boolean_terms) -> AndOrExpression:
        # Multiple terms means they are all `or`ed together
        if len(boolean_terms) > 1:
            return AndOrExpression(op="or", args=boolean_terms)
        # Just pass a single term through, nothing to `or`
        return boolean_terms[0]

    @v_args(inline=True)
    def boolean_term(self, *boolean_factors) -> AndOrExpression:
        # Multiple terms means the are all `and`ed together
        if len(boolean_factors) > 1:
            return AndOrExpression(op="and", args=boolean_factors)
        # Just pass a single term through, nothing to `and`
        return boolean_factors[0]

    # Splitting boolean_factor from `not` did not introduce issues, so we do it this
    # way to keep things cleaner.
    boolean_factor = passthrough

    @v_args(inline=True)
    def not_(self, boolean_primary) -> NotExpression:
        return NotExpression(op="not", args=(boolean_primary,))

    boolean_primary = passthrough

    # Comparison Predicate

    scalar_expression = passthrough
    comparison_predicate = passthrough

    @v_args(inline=True)
    def eq(self, *expressions) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="=", args=expressions)

    @v_args(inline=True)
    def neq(self, *expressions) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="<>", args=expressions)

    @v_args(inline=True)
    def lt(self, *expressions) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="<", args=expressions)

    @v_args(inline=True)
    def gt(self, *expressions) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op=">", args=expressions)

    @v_args(inline=True)
    def lteq(self, *expressions) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="<=", args=expressions)

    @v_args(inline=True)
    def gteq(self, *expressions) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op=">=", args=expressions)

    # Like Predicate

    pattern_expression = passthrough

    @v_args(inline=True)
    def like(self, *expressions) -> IsLikePredicate:
        return IsLikePredicate(op="like", args=expressions)

    @v_args(inline=True)
    def not_like(self, *expressions) -> NotExpression:
        return NotExpression(
            op="not", args=(IsLikePredicate(op="like", args=expressions),)
        )

    # Between Predicate

    numeric_expression = passthrough

    @v_args(inline=True)
    def is_between(self, *expressions) -> IsBetweenPredicate:
        return IsBetweenPredicate(op="between", args=expressions)

    @v_args(inline=True)
    def is_not_between(self, *expressions) -> NotExpression:
        return NotExpression(
            op="not", args=(IsBetweenPredicate(op="between", args=expressions),)
        )

    # In List Predicate

    list_values = passthrough

    @v_args(inline=True)
    def in_list(self, scalar_expression, *list_values) -> IsInListPredicate:
        return IsInListPredicate(op="in", args=[scalar_expression, list_values[0]])

    @v_args(inline=True)
    def not_in_list(self, scalar_expression, *list_values) -> NotExpression:
        return NotExpression(
            op="not",
            args=(
                IsInListPredicate(op="in", args=[scalar_expression, list_values[0]]),
            ),
        )

    # Is Null Predicate

    is_null_operand = passthrough
    is_null_predicate = passthrough

    @v_args(inline=True)
    def is_null(self, is_null_operand) -> IsNullPredicate:
        return IsNullPredicate(op="isNull", args=is_null_operand)

    @v_args(inline=True)
    def is_not_null(self, is_null_operand) -> NotExpression:
        return NotExpression(
            op="not", args=(IsNullPredicate(op="isNull", args=is_null_operand),)
        )

    # Spatial Predicate

    geom_expression = passthrough

    @v_args(inline=True)
    def spatial_predicate(
        self, spatial_operator: str, *expressions
    ) -> SpatialPredicate:
        return SpatialPredicate(op=spatial_operator.lower(), args=expressions)

    # Temporal Predicate

    temporal_expression = passthrough

    @v_args(inline=True)
    def temporal_predicate(
        self, temporal_operator: str, *expressions
    ) -> TemporalPredicate:
        return TemporalPredicate(op=temporal_operator.lower(), args=expressions)

    # Array Predicate

    array_expression = passthrough
    array_element = passthrough
    array_literal = passthrough

    @v_args(inline=True)
    def array_predicate(self, array_operator: str, *expressions) -> ArrayPredicate:
        return ArrayPredicate(op=array_operator.lower(), args=expressions)

    # Arithmetic

    arithmetic_operand = passthrough
    arithmetic_factor = passthrough
    power_term = passthrough
    arithmetic_term = passthrough
    arithmetic_expression = passthrough

    @v_args(inline=True)
    def plus(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="+", args=factors)

    @v_args(inline=True)
    def minus(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="-", args=factors)

    @v_args(inline=True)
    def multiply(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="*", args=factors)

    @v_args(inline=True)
    def divide(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="/", args=factors)

    @v_args(inline=True)
    def power(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="^", args=factors)

    @v_args(inline=True)
    def modulus(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="%", args=factors)

    @v_args(inline=True)
    def int_divide(self, *factors) -> ArithmeticExpression:
        return ArithmeticExpression(op="div", args=factors)

    @v_args(inline=True)
    def negative(self, arithmetic_operand) -> ArithmeticExpression:
        # There is not a specific json representation of `negative`, so this seems
        # like the simplest way to represent the same thing.
        return ArithmeticExpression(op="*", args=[-1, arithmetic_operand])

    # Character Literal, Function, and Property

    @v_args(inline=True)
    def CHARACTER_LITERAL(self, characters: str) -> str:
        # Strip the extra `'` off strings which are unneeded in json.
        return characters.strip("'")

    argument_list = passthrough

    @v_args(inline=True)
    def function(self, identifier: str, argument_list) -> FunctionRef:
        return FunctionRef(function=Function(name=identifier, args=argument_list))

    @v_args(inline=True)
    def property_name(self, property_name: str) -> PropertyRef:
        # Strip `"` off property names if they exist.
        return PropertyRef(property=property_name.strip('"'))

    @v_args(inline=True)
    def casei(self, character_expression) -> Casei:
        return Casei(casei=character_expression)

    @v_args(inline=True)
    def accenti(self, character_expression) -> Accenti:
        return Accenti(accenti=character_expression)

    # Spatial Definitions

    coordinate = passthrough
    # Need this extra inline here or point coordinates are nested too deep
    point_coordinates = v_args(inline=True)(passthrough)

    @v_args(inline=True)
    def point(self, coordinates) -> Point:
        return Point(type="Point", coordinates=coordinates)

    linestring_coordinates = passthrough

    @v_args(inline=True)
    def linestring(self, coordinates) -> LineString:
        return LineString(type="LineString", coordinates=coordinates)

    linear_ring_coordinates = passthrough
    polygon_coordinates = passthrough

    @v_args(inline=True)
    def polygon(self, coordinates) -> Polygon:
        return Polygon(type="Polygon", coordinates=coordinates)

    multi_point_coordinates = passthrough

    @v_args(inline=True)
    def multi_point(self, coordinates) -> MultiPoint:
        return MultiPoint(type="MultiPoint", coordinates=coordinates)

    multi_linestring_coordinates = passthrough

    @v_args(inline=True)
    def multi_linestring(self, coordinates) -> MultiLineString:
        return MultiLineString(type="MultiLineString", coordinates=coordinates)

    multi_polygon_coordinates = passthrough

    @v_args(inline=True)
    def multi_polygon(self, coordinates) -> MultiPolygon:
        return MultiPolygon(type="MultiPolygon", coordinates=coordinates)

    def geometry_collection(self, geometries) -> GeometryCollection:
        return GeometryCollection(type="GeometryCollection", geometries=geometries)

    @v_args(inline=True)
    def bbox(self, *coordinates) -> BboxLiteral:
        return BboxLiteral(bbox=coordinates)

    # Date and Time Definitions

    def DATE(self, datestring: str) -> date:
        # Simple `strptime` can be used to parse the date.
        return datetime.strptime(datestring, "%Y-%m-%d").date()

    def DATE_TIME(self, datetimestring: str) -> datetime:
        # Do some processing to account for optional decimal seconds within the text.

        # Remove the `Z` that is always at the end of the string.
        datetimestring = datetimestring[:-1]
        # Look for a `.` to determine if optional fractional seconds were included.
        if "." not in datetimestring:
            # Add a `.0` to the end if they were not included
            datetimestring = datetimestring + ".0"
        # Now a single `strptime` can be used to parse the input. It is always Z, so
        # timezone needs to be set to UTC.
        return datetime.strptime(datetimestring, "%Y-%m-%dT%H:%M:%S.%f").replace(
            tzinfo=timezone.utc
        )

    @v_args(inline=True)
    def date_instant(self, date_: date) -> DateLiteral:
        return DateLiteral(date=date_)

    @v_args(inline=True)
    def timestamp_instant(self, timestamp: datetime) -> TimestampLiteral:
        return TimestampLiteral(timestamp=timestamp)

    @v_args(inline=True)
    def interval_literal(self, *interval) -> IntervalLiteral:
        return IntervalLiteral(interval=interval)


parser = Lark.open(
    "pycql2/cql2.lark",
    start="boolean_expression",
    maybe_placeholders=False,
)
transformer = Cql2Transformer()
