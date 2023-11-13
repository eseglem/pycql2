from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Literal,
    MutableSequence,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from geojson_pydantic.geometries import Geometry, GeometryCollection
from geojson_pydantic.types import BBox
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidatorFunctionWrapHandler,
    model_validator,
)
from typing_extensions import Annotated

# The use of `Strict*` is necessary in a few places because pydantic will convert
# booleans to numbers and vice versa. As well as various types to strings. This
# should hopefully be fixed by Pydantic v2.

# Since we are using strict, we need to use a union to allow for ints and floats
# in places we want to have numbers.
StrictFloatOrInt = Union[StrictFloat, StrictInt]


def make_char_literal(string: str) -> str:
    # Escape any single quotes with an extra one.
    # Monitor https://github.com/opengeospatial/ogcapi-features/issues/717
    return "'" + string.replace("'", "''") + "'"


def join_list(items: Sequence, sep: str) -> str:
    return sep.join(str(item) for item in items)


class NotExpression(BaseModel):
    op: Literal["not"]
    args: Tuple[BooleanExpression]

    def __str__(self) -> str:
        return f"NOT {self.args[0]}"


class BinaryComparisonPredicate(BaseModel):
    op: Literal["=", "<>", "<", "<=", ">", ">="]
    args: Tuple[ScalarExpression, ScalarExpression]

    def __str__(self) -> str:
        return f"{self.args[0]} {self.op} {self.args[1]}"


class IsLikePredicate(BaseModel):
    op: Literal["like"]
    args: Tuple[CharacterExpression, PatternExpression]

    def __str__(self) -> str:
        return f"{self.args[0]} LIKE {self.args[1]}"


class IsBetweenPredicate(BaseModel):
    op: Literal["between"]
    args: Tuple[NumericExpression, NumericExpression, NumericExpression]

    def __str__(self) -> str:
        return f"{self.args[0]} BETWEEN {self.args[1]} AND {self.args[2]}"


class IsInListPredicate(BaseModel):
    op: Literal["in"]
    args: Tuple[ScalarExpression, List[ScalarExpression]]

    def __str__(self) -> str:
        return f"{self.args[0]} IN ({join_list(self.args[1], ', ')})"


class IsNullPredicate(BaseModel):
    op: Literal["isNull"]
    args: IsNullOperand

    def __str__(self) -> str:
        return f"{self.args} IS NULL"


class SpatialOperator(str, Enum):
    s_contains = "s_contains"
    s_crosses = "s_crosses"
    s_disjoint = "s_disjoint"
    s_equals = "s_equals"
    s_intersects = "s_intersects"
    s_overlaps = "s_overlaps"
    s_touches = "s_touches"
    s_within = "s_within"


class SpatialPredicate(BaseModel):
    op: SpatialOperator
    args: Tuple[GeomExpression, GeomExpression]

    def __str__(self) -> str:
        return f"{self.op.upper()}({self.args[0]}, {self.args[1]})"


class TemporalOperator(str, Enum):
    t_after = "t_after"
    t_before = "t_before"
    t_contains = "t_contains"
    t_disjoint = "t_disjoint"
    t_during = "t_during"
    t_equals = "t_equals"
    t_finishedBy = "t_finishedBy"
    t_finishes = "t_finishes"
    t_intersects = "t_intersects"
    t_meets = "t_meets"
    t_metBy = "t_metBy"
    t_overlappedBy = "t_overlappedBy"
    t_overlaps = "t_overlaps"
    t_startedBy = "t_startedBy"
    t_starts = "t_starts"


class TemporalPredicate(BaseModel):
    op: TemporalOperator
    args: Tuple[TemporalExpression, TemporalExpression]

    def __str__(self) -> str:
        return f"{self.op.upper()}({self.args[0]}, {self.args[1]})"


class Array(RootModel):
    root: MutableSequence[ArrayElement]

    def __str__(self) -> str:
        return f"({join_list(self.root, ', ')})"


class ArrayExpression(BaseModel):
    root: Tuple[ArrayExpressionItems, ArrayExpressionItems]

    def __str__(self) -> str:
        return f"({self.root[0]}, {self.root[1]})"

    @model_validator(mode="wrap")
    @classmethod
    def validate_root(
        cls, values: Any, handler: ValidatorFunctionWrapHandler
    ) -> ArrayExpression:
        # When input from json lists don't get validated this way
        if isinstance(values, Sequence) and len(values) == 2:
            return ArrayExpression(root=values)  # type: ignore [arg-type]
        result = handler(values)
        return result


class ArrayOperator(str, Enum):
    a_containedBy = "a_containedBy"
    a_contains = "a_contains"
    a_equals = "a_equals"
    a_overlaps = "a_overlaps"


class ArrayPredicate(BaseModel):
    op: ArrayOperator
    args: ArrayExpression

    def __str__(self) -> str:
        return f"{self.op.upper()}{self.args}"


class BooleanExpression(RootModel):
    root: BooleanExpressionItems

    def __str__(self) -> str:
        # If it's a bool, we uppercase it.
        if isinstance(self.root, bool):
            return str(self.root).upper()
        # Otherwise, we return the string representation of the root.
        return str(self.root)


# Type checking does not like `conlist`, so use a conditional here to avoid the error.
# Due to the recursive nature of the grammar we cannot use `Field` here because it
# does not properly enforce min / max items when nested. May be fixed by pydantic2.
if TYPE_CHECKING:
    BooleanExpressionList = List[BooleanExpression]
else:
    BooleanExpressionList = Annotated[List[BooleanExpression], Field(min_length=2)]


class AndOrExpression(BaseModel):
    op: Literal["or", "and"]
    args: BooleanExpressionList

    def __str__(self) -> str:
        # May result in excessive parens, but guarantees correctness.
        return f"({join_list(self.args, f' {self.op.upper()} ')})"


class ArithmeticExpression(BaseModel):
    # cql2-text defines two operators cql2-json does not.
    op: Literal["+", "-", "*", "/", "^", "%", "div"]
    args: Tuple[ArithmeticOperandsItems, ArithmeticOperandsItems]

    def __str__(self) -> str:
        # May result in excessive parens, but guarantees correctness
        return f"({self.args[0]} {self.op} {self.args[1]})"


class Function(BaseModel):
    name: StrictStr
    args: FunctionArguments = None

    def __str__(self) -> str:
        # If self.args, comma join them. Otherwise, empty string. Inside parens.
        return self.name + "(" + (join_list(self.args, ", ") if self.args else "") + ")"


class FunctionRef(BaseModel):
    function: Function

    def __str__(self) -> str:
        return str(self.function)


class PropertyRef(BaseModel):
    property: StrictStr

    def __str__(self) -> str:
        # May not need to be quoted, but it can be, so its safer and easier
        return f'"{self.property}"'


class DateInstant(BaseModel):
    date: date

    def __str__(self) -> str:
        return f"DATE('{self.date.isoformat()}')"


class TimestampInstant(BaseModel):
    timestamp: datetime

    def __str__(self) -> str:
        # format it as iso with `Z` at the end. Note this will always include the
        # microseconds, even if they are 0.
        return f"TIMESTAMP('{self.timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}')"


class BboxLiteral(BaseModel):
    bbox: BBox

    def __str__(self) -> str:
        return f"BBOX{self.bbox}"


class IntervalArrayItems(RootModel):
    root: Union[datetime, date, Literal[".."], PropertyRef, FunctionRef]

    def __str__(self) -> str:
        # If it is a datetime, format it as iso with `Z` at the end. Note this will
        # always include the microseconds, even if they are 0.
        if isinstance(self.root, datetime):
            return f"""'{self.root.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}'"""
        # If it is a date, format with built-in isoformat
        if isinstance(self.root, date):
            return f"'{self.root.isoformat()}'"
        if self.root == "..":
            return "'..'"
        # Otherwise use the string representation of the root.
        return str(self.root)


class IntervalInstance(BaseModel):
    interval: Tuple[IntervalArrayItems, IntervalArrayItems]

    def __str__(self) -> str:
        return f"INTERVAL({self.interval[0]}, {self.interval[1]})"


class CharacterExpression(RootModel):
    root: CharacterExpressionItems

    def __str__(self) -> str:
        # If it is already a string, make it a char literal
        if isinstance(self.root, str):
            return make_char_literal(self.root)
        # Otherwise, return the string representation of the root
        return str(self.root)


class PatternExpression(RootModel):
    root: PatternExpressionItems

    def __str__(self) -> str:
        # If it is already a string, make it a char literal
        if isinstance(self.root, str):
            return make_char_literal(self.root)
        # Otherwise, return the string representation of the root
        return str(self.root)


E = TypeVar("E", bound=Union[CharacterExpression, PatternExpression])


class Casei(BaseModel, Generic[E]):
    casei: E

    def __str__(self) -> str:
        return f"CASEI({self.casei})"


class Accenti(BaseModel, Generic[E]):
    accenti: E

    def __str__(self) -> str:
        return f"ACCENTI({self.accenti})"


class GeometryLiteral(RootModel):
    root: Union[Geometry, GeometryCollection]

    def __str__(self) -> str:
        return self.root.wkt


ComparisonPredicate = Union[
    BinaryComparisonPredicate,
    IsLikePredicate,
    IsBetweenPredicate,
    IsInListPredicate,
    IsNullPredicate,
]
InstantInstance = Union[DateInstant, TimestampInstant]
NumericExpression = Union[
    ArithmeticExpression, StrictFloatOrInt, PropertyRef, FunctionRef
]
SpatialInstance = Union[GeometryLiteral, BboxLiteral]
GeomExpression = Union[SpatialInstance, PropertyRef, FunctionRef]
TemporalInstance = Union[InstantInstance, IntervalInstance]
TemporalExpression = Union[TemporalInstance, PropertyRef, FunctionRef]
TemporalInstantExpression = Union[InstantInstance, PropertyRef, FunctionRef]
ScalarExpression = Union[
    TemporalInstantExpression, BooleanExpression, CharacterExpression, NumericExpression
]
ArithmeticOperandsItems = Union[
    ArithmeticExpression, PropertyRef, FunctionRef, StrictFloatOrInt
]
ArrayExpressionItems = Union[Array, PropertyRef, FunctionRef]
PatternExpressionItems = Union[
    Casei[PatternExpression], Accenti[PatternExpression], StrictStr
]
CharacterExpressionItems = Union[
    Casei[CharacterExpression],
    Accenti[CharacterExpression],
    StrictStr,
    PropertyRef,
    FunctionRef,
]

# Extra types to match the cql2-text grammar better
IsNullOperand = Union[
    CharacterExpression,
    NumericExpression,
    TemporalExpression,
    BooleanExpression,
    GeomExpression,
]
ArrayElement = Union[
    CharacterExpression,
    NumericExpression,
    BooleanExpression,
    GeomExpression,
    TemporalExpression,
    Array,
]
FunctionArguments = Union[
    None,
    List[
        Union[
            CharacterExpression,
            NumericExpression,
            BooleanExpression,
            GeomExpression,
            TemporalExpression,
            Array,
        ]
    ],
]
BooleanExpressionItems = Union[
    AndOrExpression,
    NotExpression,
    ComparisonPredicate,
    SpatialPredicate,
    TemporalPredicate,
    ArrayPredicate,
    StrictBool,
]

# Update all the forward references
Accenti.model_rebuild()
AndOrExpression.model_rebuild()
ArithmeticExpression.model_rebuild()
ArrayExpression.model_rebuild()
ArrayPredicate.model_rebuild()
BboxLiteral.model_rebuild()
BinaryComparisonPredicate.model_rebuild()
BooleanExpression.model_rebuild()
Casei.model_rebuild()
CharacterExpression.model_rebuild()
DateInstant.model_rebuild()
Function.model_rebuild()
FunctionRef.model_rebuild()
IntervalInstance.model_rebuild()
IsBetweenPredicate.model_rebuild()
IsInListPredicate.model_rebuild()
IsLikePredicate.model_rebuild()
IsNullPredicate.model_rebuild()
NotExpression.model_rebuild()
PatternExpression.model_rebuild()
PropertyRef.model_rebuild()
SpatialPredicate.model_rebuild()
TemporalPredicate.model_rebuild()
TimestampInstant.model_rebuild()
