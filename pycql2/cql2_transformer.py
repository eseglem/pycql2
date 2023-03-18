from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, List, Union, cast

from geojson_pydantic import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from geojson_pydantic.geometries import Geometry
from geojson_pydantic.types import (
    LineStringCoords,
    MultiLineStringCoords,
    MultiPointCoords,
    MultiPolygonCoords,
    PolygonCoords,
    Position,
)
from lark import Lark, Transformer, v_args

from pycql2.cql2_pydantic import (
    Accenti,
    AndOrExpression,
    ArithmeticExpression,
    ArithmeticOperandsItems,
    Array,
    ArrayElement,
    ArrayExpression,
    ArrayExpressionItems,
    ArrayOperator,
    ArrayPredicate,
    BboxLiteral,
    BinaryComparisonPredicate,
    BooleanExpression,
    BooleanExpressionItems,
    Casei,
    CharacterExpression,
    CharacterExpressionItems,
    DateInstant,
    Function,
    FunctionArguments,
    FunctionRef,
    GeomExpression,
    IntervalArrayItems,
    IntervalInstance,
    IsBetweenPredicate,
    IsInListPredicate,
    IsLikePredicate,
    IsNullOperand,
    IsNullPredicate,
    NotExpression,
    NumericExpression,
    PatternExpression,
    PatternExpressionItems,
    PropertyRef,
    ScalarExpression,
    SpatialOperator,
    SpatialPredicate,
    StrictFloatOrInt,
    TemporalExpression,
    TemporalOperator,
    TemporalPredicate,
    TimestampInstant,
)

BooleanExpressionOrItems = Union[BooleanExpression, BooleanExpressionItems]
Predicate = Union[
    BinaryComparisonPredicate, SpatialPredicate, TemporalPredicate, ArrayPredicate
]
BooleanPrimary = Union[Predicate, bool, BooleanExpression]
BooleanFactor = Union[BooleanPrimary, NotExpression]
BooleanTerm: Union[BooleanFactor, AndOrExpression]


def _passthrough(_self: Cql2Transformer, args: Any) -> Any:
    """Pass the arguments up to the next level of the tree.

    This is utilized throughout the Transformer when additional parsing
    is not necessary.
    """
    return args


def _make_boolean_expression(arg: BooleanExpressionOrItems) -> BooleanExpression:
    """Ensure arg is a BooleanExpression."""
    if not isinstance(arg, BooleanExpression):
        arg = BooleanExpression(__root__=arg)
    return arg


class Cql2Transformer(Transformer):
    """Transformer that turns parsed cql2-text into cql2-json."""

    # Treat all signed numbers as floats
    SIGNED_NUMBER = float

    @v_args(inline=True)
    def BOOLEAN_LITERAL(self, boolean_literal: str) -> bool:
        # Text is case insensitive, so upper it and compare with "TRUE"
        return boolean_literal.upper() == "TRUE"

    # Since we are using `?` in the grammar it will pass through single items
    # and we want to ensure that the output is always a `BooleanExpression`.
    @v_args(inline=True)
    def start(self, expression: BooleanExpressionOrItems) -> BooleanExpression:
        return _make_boolean_expression(expression)

    # All contiguous blocks of `or` / `and` are grouped together into single
    # AndOrExpression.

    # We end up with an awkward situation where we need to use the `boolean_*`
    # functions to handle the `or` and `and` cases. Any attempt to handle the
    # single item case in the `boolean_*` functions greatly increased the complexity
    # of the transformer and makes it harder to understand. The cleanest way to
    # handle it was put the final `BooleanExpression` logic in the `start` function.

    def boolean_expression(
        self, boolean_terms: List[BooleanExpressionOrItems]
    ) -> AndOrExpression:
        # The List will always have at least two items, if it doesn't then the
        # parser will pass it up to `start`
        return AndOrExpression(
            op="or", args=[_make_boolean_expression(t) for t in boolean_terms]
        )

    def boolean_term(
        self, boolean_factors: List[BooleanExpressionOrItems]
    ) -> AndOrExpression:
        # The List will always have at least two items, if it doesn't then the
        # parser will pass it up to `boolean_expression`
        return AndOrExpression(
            op="and", args=[_make_boolean_expression(f) for f in boolean_factors]
        )

    @v_args(inline=True)
    def not_(self, boolean_primary: BooleanPrimary) -> NotExpression:
        boolean_primary = _make_boolean_expression(boolean_primary)
        return NotExpression(op="not", args=(boolean_primary,))

    # Comparison Predicate

    @v_args(inline=True)
    def eq(
        self, e1: ScalarExpression, e2: ScalarExpression
    ) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="=", args=(e1, e2))

    @v_args(inline=True)
    def neq(
        self, e1: ScalarExpression, e2: ScalarExpression
    ) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="<>", args=(e1, e2))

    @v_args(inline=True)
    def lt(
        self, e1: ScalarExpression, e2: ScalarExpression
    ) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="<", args=(e1, e2))

    @v_args(inline=True)
    def gt(
        self, e1: ScalarExpression, e2: ScalarExpression
    ) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op=">", args=(e1, e2))

    @v_args(inline=True)
    def lteq(
        self, e1: ScalarExpression, e2: ScalarExpression
    ) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op="<=", args=(e1, e2))

    @v_args(inline=True)
    def gteq(
        self, e1: ScalarExpression, e2: ScalarExpression
    ) -> BinaryComparisonPredicate:
        return BinaryComparisonPredicate(op=">=", args=(e1, e2))

    # Like Predicate

    @v_args(inline=True)
    def pattern_expression(self, arg: PatternExpressionItems) -> PatternExpression:
        return PatternExpression(__root__=arg)

    @v_args(inline=True)
    def character_expression(
        self, arg: CharacterExpressionItems
    ) -> CharacterExpression:
        return CharacterExpression(__root__=arg)

    @v_args(inline=True)
    def like(self, e1: CharacterExpression, e2: PatternExpression) -> IsLikePredicate:
        return IsLikePredicate(op="like", args=(e1, e2))

    @v_args(inline=True)
    def not_like(self, e1: CharacterExpression, e2: PatternExpression) -> NotExpression:
        return NotExpression(
            op="not",
            args=(
                BooleanExpression(__root__=IsLikePredicate(op="like", args=(e1, e2))),
            ),
        )

    # Between Predicate

    @v_args(inline=True)
    def is_between(
        self, e1: NumericExpression, e2: NumericExpression, e3: NumericExpression
    ) -> IsBetweenPredicate:
        return IsBetweenPredicate(op="between", args=(e1, e2, e3))

    @v_args(inline=True)
    def is_not_between(
        self, e1: NumericExpression, e2: NumericExpression, e3: NumericExpression
    ) -> NotExpression:
        return NotExpression(
            op="not",
            args=(
                BooleanExpression(
                    __root__=IsBetweenPredicate(op="between", args=(e1, e2, e3))
                ),
            ),
        )

    # In List Predicate

    list_values = _passthrough

    @v_args(inline=True)
    def in_list(
        self, scalar_expression: ScalarExpression, list_values: List[ScalarExpression]
    ) -> IsInListPredicate:
        return IsInListPredicate(op="in", args=(scalar_expression, list_values))

    @v_args(inline=True)
    def not_in_list(
        self, scalar_expression: ScalarExpression, *list_values: List[ScalarExpression]
    ) -> NotExpression:
        return NotExpression(
            op="not",
            args=(
                BooleanExpression(
                    __root__=IsInListPredicate(
                        op="in", args=(scalar_expression, list_values[0])
                    )
                ),
            ),
        )

    # Is Null Predicate

    @v_args(inline=True)
    def is_null(self, is_null_operand: IsNullOperand) -> IsNullPredicate:
        return IsNullPredicate(op="isNull", args=is_null_operand)

    @v_args(inline=True)
    def is_not_null(self, is_null_operand: IsNullOperand) -> NotExpression:
        return NotExpression(
            op="not",
            args=(
                BooleanExpression(
                    __root__=IsNullPredicate(op="isNull", args=is_null_operand)
                ),
            ),
        )

    # Spatial Predicate

    @v_args(inline=True)
    def spatial_predicate(
        self, spatial_operator: str, e1: GeomExpression, e2: GeomExpression
    ) -> SpatialPredicate:
        op = SpatialOperator(spatial_operator.lower())
        return SpatialPredicate(op=op, args=(e1, e2))

    # Temporal Predicate

    @v_args(inline=True)
    def temporal_predicate(
        self, temporal_operator: str, e1: TemporalExpression, e2: TemporalExpression
    ) -> TemporalPredicate:
        op = temporal_operator.lower()
        # Special case for any operation that ends with `by`
        if op.endswith("by"):
            op = op[:-2] + "By"
        op = TemporalOperator(op)
        return TemporalPredicate(op=op, args=(e1, e2))

    # Array Predicate

    @v_args(inline=True)
    def array(self, *array_elements: ArrayElement) -> Array:
        return Array(__root__=list(array_elements))

    @v_args(inline=True)
    def array_predicate(
        self, array_operator: str, e1: ArrayExpressionItems, e2: ArrayExpressionItems
    ) -> ArrayPredicate:
        op = array_operator.lower()
        # Special case for any operation that ends with `by`
        if op.endswith("by"):
            op = op[:-2] + "By"
        op = ArrayOperator(op)
        return ArrayPredicate(op=op, args=ArrayExpression(__root__=(e1, e2)))

    # Arithmetic

    @v_args(inline=True)
    def plus(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="+", args=(o1, o2))

    @v_args(inline=True)
    def minus(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="-", args=(o1, o2))

    @v_args(inline=True)
    def multiply(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="*", args=(o1, o2))

    @v_args(inline=True)
    def divide(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="/", args=(o1, o2))

    @v_args(inline=True)
    def power(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="^", args=(o1, o2))

    @v_args(inline=True)
    def modulus(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="%", args=(o1, o2))

    @v_args(inline=True)
    def int_divide(
        self, o1: ArithmeticOperandsItems, o2: ArithmeticOperandsItems
    ) -> ArithmeticExpression:
        return ArithmeticExpression(op="div", args=(o1, o2))

    @v_args(inline=True)
    def negative(
        self, arithmetic_operand: Union[StrictFloatOrInt, PropertyRef, FunctionRef]
    ) -> ArithmeticExpression:
        # `arithmetic_factor` only allows negative on `arithmetic_operand` as defined
        # in the bnf, which does not include `arithmetic_expression`.  So we cannot use
        # `ArithmeticOperandsItems` here.

        # There is not a specific json representation of `negative`, so this seems
        # like the simplest way to represent the same thing.
        return ArithmeticExpression(op="*", args=(-1, arithmetic_operand))

    # Character Literal, Function, and Property

    @v_args(inline=True)
    def CHARACTER_LITERAL(self, characters: str) -> str:
        # Strip the extra `'` off strings which are unneeded in json.
        return characters.strip("'")

    argument_list = _passthrough

    @v_args(inline=True)
    def function(
        self, identifier: str, argument_list: FunctionArguments = None
    ) -> FunctionRef:
        # Argument list is optional, so default to `None` if not provided.
        return FunctionRef(function=Function(name=identifier, args=argument_list))

    @v_args(inline=True)
    def property_name(self, property_name: str) -> PropertyRef:
        # Strip `"` off property names if they exist.
        return PropertyRef(property=property_name.strip('"'))

    @v_args(inline=True)
    def casei(self, character_expression: CharacterExpression) -> Casei:
        return Casei(casei=character_expression)

    @v_args(inline=True)
    def accenti(self, character_expression: CharacterExpression) -> Accenti:
        return Accenti(accenti=character_expression)

    # Spatial Definitions

    def coordinate(self, coordinate: List[float]) -> Position:
        # We know coordinate will always be 2 or 3 elements, so we can just cast it
        return cast(Position, tuple(coordinate))

    # Need this inline or point coordinates would be nested too deep. This will be
    # a `Position`
    point_coordinates = v_args(inline=True)(_passthrough)

    @v_args(inline=True)
    def point(self, coordinates: Position) -> Point:
        return Point(type="Point", coordinates=coordinates)

    # This is a `LineStringCoords`
    linestring_coordinates = _passthrough

    @v_args(inline=True)
    def linestring(self, coordinates: LineStringCoords) -> LineString:
        return LineString(type="LineString", coordinates=coordinates)

    # This is a `LinearRingCoords` for use in `PolygonCoords`
    linear_ring_coordinates = _passthrough
    # This is a `PolygonCoords`
    polygon_coordinates = _passthrough

    @v_args(inline=True)
    def polygon(self, coordinates: PolygonCoords) -> Polygon:
        return Polygon(type="Polygon", coordinates=coordinates)

    # This is a `MultiPointCoords`
    multi_point_coordinates = _passthrough

    @v_args(inline=True)
    def multi_point(self, coordinates: MultiPointCoords) -> MultiPoint:
        return MultiPoint(type="MultiPoint", coordinates=coordinates)

    # This is a `MultiLineStringCoords`
    multi_linestring_coordinates = _passthrough

    @v_args(inline=True)
    def multi_linestring(self, coordinates: MultiLineStringCoords) -> MultiLineString:
        return MultiLineString(type="MultiLineString", coordinates=coordinates)

    # This is a `MultiPolygonCoords`
    multi_polygon_coordinates = _passthrough

    @v_args(inline=True)
    def multi_polygon(self, coordinates: MultiPolygonCoords) -> MultiPolygon:
        return MultiPolygon(type="MultiPolygon", coordinates=coordinates)

    def geometry_collection(self, geometries: List[Geometry]) -> GeometryCollection:
        return GeometryCollection(type="GeometryCollection", geometries=geometries)

    @v_args(inline=True)
    def bbox(self, *coordinates: float) -> BboxLiteral:
        # We know that `coordinates` will always be 4 or 6, so we can just use the
        # tuple directly. But mypy doesn't know that, so we need to ignore the
        # type error.
        return BboxLiteral(bbox=coordinates)  # type: ignore[arg-type]

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
    def DOTDOT(self, dotdot: str) -> str:
        # Strip the `'` which aren't used in the json representation
        return dotdot.strip("'")

    @v_args(inline=True)
    def date_instant(self, date_: date) -> DateInstant:
        return DateInstant(date=date_)

    @v_args(inline=True)
    def timestamp_instant(self, timestamp: datetime) -> TimestampInstant:
        return TimestampInstant(timestamp=timestamp)

    @v_args(inline=True)
    def interval_instance(
        self, i1: IntervalArrayItems, i2: IntervalArrayItems
    ) -> IntervalInstance:
        return IntervalInstance(interval=(i1, i2))


parser = Lark.open(
    "cql2.lark",
    rel_to=__file__,
    start="start",
    maybe_placeholders=False,
)
transformer = Cql2Transformer()
