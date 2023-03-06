from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Sequence, Union

from geojson_pydantic.geometries import Geometry
from geojson_pydantic.types import BBox
from pydantic import BaseModel, StrictBool, StrictStr, conlist


def make_char_literal(string: str) -> str:
    # Escape any single quotes with an extra one.
    # Monitor https://github.com/opengeospatial/ogcapi-features/issues/717
    return "'" + string.replace("'", "''") + "'"


def join_list(items: Sequence, sep: str) -> str:
    return sep.join(str(item) for item in items)


class NotExpression(BaseModel):
    op: Literal["not"]
    args: tuple[BooleanExpression]

    def __str__(self) -> str:
        return f"NOT {self.args[0]}"


class BinaryComparisonPredicate(BaseModel):
    op: Literal["=", "<>", "<", "<=", ">", ">="]
    args: tuple[ScalarExpression, ScalarExpression]

    def __str__(self) -> str:
        return f"{self.args[0]} {self.op} {self.args[1]}"


class IsLikePredicate(BaseModel):
    op: Literal["like"]
    args: tuple[CharacterExpression, StrictStr | Casei | Accenti]

    def __str__(self) -> str:
        # If the second argument is a string, we need to make it a char literal.
        args1 = self.args[1]
        if isinstance(args1, str):
            args1 = make_char_literal(args1)
        # Then we return the string representation no matter what.
        return f"{self.args[0]} LIKE {args1}"


class IsBetweenPredicate(BaseModel):
    op: Literal["between"]
    args: tuple[NumericExpression, NumericExpression, NumericExpression]

    def __str__(self) -> str:
        return f"{self.args[0]} BETWEEN {self.args[1]} AND {self.args[2]}"


class IsInListPredicate(BaseModel):
    op: Literal["in"]
    args: tuple[ScalarExpression, list[ScalarExpression]]

    def __str__(self) -> str:
        return f"{self.args[0]} IN ({join_list(self.args[1], ', ')})"


class IsNullPredicate(BaseModel):
    op: Literal["isNull"]
    args: (
        CharacterExpression
        | NumericExpression
        | TemporalExpression
        | BooleanExpression
        | GeomExpression
    )

    def __str__(self) -> str:
        return f"{self.args} IS NULL"


class SpatialPredicate(BaseModel):
    op: Literal[
        "s_contains",
        "s_crosses",
        "s_disjoint",
        "s_equals",
        "s_intersects",
        "s_overlaps",
        "s_touches",
        "s_within",
    ]
    args: tuple[GeomExpression, GeomExpression]

    def __str__(self) -> str:
        return f"{self.op.upper()}({self.args[0]}, {self.args[1]})"


class TemporalPredicate(BaseModel):
    op: Literal[
        "t_after",
        "t_before",
        "t_contains",
        "t_disjoint",
        "t_during",
        "t_equals",
        "t_finishedBy",
        "t_finishes",
        "t_intersects",
        "t_meets",
        "t_metBy",
        "t_overlappedBy",
        "t_overlaps",
        "t_startedBy",
        "t_starts",
    ]
    args: tuple[TemporalExpression, TemporalExpression]

    def __str__(self) -> str:
        return f"{self.op.upper()}({self.args[0]}, {self.args[1]})"


class ArrayLiteral(BaseModel):
    __root__: list[
        (
            NumericExpression
            | BooleanExpression
            | GeomExpression
            | TemporalExpression
            | list[ArrayLiteral]
            | CharacterExpression
        )
    ]

    def __str__(self) -> str:
        return f"({join_list(self.__root__, ', ')})"


class ArrayPredicate(BaseModel):
    op: Literal["a_containedBy", "a_contains", "a_equals", "a_overlaps"]
    args: ArrayExpression

    def __str__(self) -> str:
        return f"{self.op.upper()}{self.args}"


class BooleanExpression(BaseModel):
    __root__: (
        AndOrExpression
        | NotExpression
        | ComparisonPredicate
        | SpatialPredicate
        | TemporalPredicate
        | ArrayPredicate
        | StrictBool
    )

    def __str__(self) -> str:
        # If it's a bool, we uppercase it.
        if isinstance(self.__root__, bool):
            return str(self.__root__).upper()
        # Otherwise, we return the string representation of the root.
        return str(self.__root__)


class AndOrExpression(BaseModel):
    op: Literal["or", "and"]
    args: conlist(item_type=BooleanExpression, min_items=2)  # type: ignore[valid-type]
    # Cannot use `Field` here because everything is recursive and it does not properly
    # enforce min / max items on anything. May be fixed by pydantic2.

    def __str__(self) -> str:
        # May result in excessive parens, but guarantees correctness.
        return f"({join_list(self.args, f' {self.op.upper()} ')})"


class ArithmeticExpression(BaseModel):
    # cql2-text defines two operators cql2-json does not.
    op: Literal["+", "-", "*", "/", "^", "%", "div"]
    args: tuple[ArithmeticOperandsItems, ArithmeticOperandsItems]

    def __str__(self) -> str:
        # May result in excessive parens, but guarantees correctness
        return f"({self.args[0]} {self.op} {self.args[1]})"


class Function(BaseModel):
    name: StrictStr
    args: None | (
        list[
            (
                CharacterExpression
                | NumericExpression
                | BooleanExpression
                | GeomExpression
                | TemporalExpression
                | ArrayExpression
            )
        ]
    ) = None

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


ArrayExpressionItems = Union[ArrayLiteral, PropertyRef, FunctionRef]


class ArrayExpression(BaseModel):
    __root__ = tuple[ArrayExpressionItems, ArrayExpressionItems]

    def __str__(self) -> str:
        return f"({self.__root__[0]}, {self.__root__[1]})"

    class Config:
        arbitrary_types_allowed = True


class DateLiteral(BaseModel):
    date: date

    def __str__(self) -> str:
        return f"DATE('{self.date.isoformat()}')"


class TimestampLiteral(BaseModel):
    timestamp: datetime

    def __str__(self) -> str:
        # format it as iso with `Z` at the end. Note this will always include the
        # microseconds, even if they are 0.
        return f"TIMESTAMP('{self.timestamp.strftime('%Y-%m-%dT%H:%M:%S.%fZ')}')"


class Casei(BaseModel):
    casei: CharacterExpression

    def __str__(self) -> str:
        return f"CASEI({self.casei})"


class Accenti(BaseModel):
    accenti: CharacterExpression

    def __str__(self) -> str:
        return f"ACCENTI({self.accenti})"


class BboxLiteral(BaseModel):
    bbox: BBox

    def __str__(self) -> str:
        return f"BBOX{self.bbox}"


class IntervalArrayItems(BaseModel):
    __root__: datetime | date | Literal[".."] | PropertyRef | FunctionRef

    def __str__(self) -> str:
        # If it is a datetime, format it as iso with `Z` at the end. Note this will
        # always include the microseconds, even if they are 0.
        if isinstance(self.__root__, datetime):
            return f"""'{self.__root__.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}'"""
        # If it is a date, format with built-in isoformat
        if isinstance(self.__root__, date):
            return f"'{self.__root__.isoformat()}'"
        if self.__root__ == "..":
            return "'..'"
        # Otherwise use the string representation of the root.
        return str(self.__root__)


class IntervalLiteral(BaseModel):
    interval: tuple[IntervalArrayItems, IntervalArrayItems]

    def __str__(self) -> str:
        return f"INTERVAL({self.interval[0]}, {self.interval[1]})"


class CharacterExpression(BaseModel):
    __root__: Casei | Accenti | StrictStr | PropertyRef | FunctionRef

    def __str__(self) -> str:
        # If it is already a string, make it a char literal
        if isinstance(self.__root__, str):
            return make_char_literal(self.__root__)
        # Otherwise, return the string representation of the root
        return str(self.__root__)


class GeometryLiteral(BaseModel):
    __root__: Geometry

    def __str__(self) -> str:
        return self.__root__.wkt


ComparisonPredicate = Union[
    BinaryComparisonPredicate,
    IsLikePredicate,
    IsBetweenPredicate,
    IsInListPredicate,
    IsNullPredicate,
]
InstantLiteral = Union[DateLiteral, TimestampLiteral]
NumericExpression = Union[ArithmeticExpression, float, PropertyRef, FunctionRef]
SpatialLiteral = Union[GeometryLiteral, BboxLiteral]
GeomExpression = Union[SpatialLiteral, PropertyRef, FunctionRef]
TemporalLiteral = Union[InstantLiteral, IntervalLiteral]
TemporalExpression = Union[TemporalLiteral, PropertyRef, FunctionRef]
TemporalInstantExpression = Union[InstantLiteral, PropertyRef, FunctionRef]
ScalarExpression = Union[
    TemporalInstantExpression, BooleanExpression, CharacterExpression, NumericExpression
]
ArithmeticOperandsItems = Union[ArithmeticExpression, PropertyRef, FunctionRef, float]

AndOrExpression.update_forward_refs()
NotExpression.update_forward_refs()
BinaryComparisonPredicate.update_forward_refs()
IsLikePredicate.update_forward_refs()
IsBetweenPredicate.update_forward_refs()
IsInListPredicate.update_forward_refs()
IsNullPredicate.update_forward_refs()
SpatialPredicate.update_forward_refs()
TemporalPredicate.update_forward_refs()
ArrayPredicate.update_forward_refs()
BooleanExpression.update_forward_refs()
ArithmeticExpression.update_forward_refs()
Function.update_forward_refs()
FunctionRef.update_forward_refs()
PropertyRef.update_forward_refs()
DateLiteral.update_forward_refs()
TimestampLiteral.update_forward_refs()
Casei.update_forward_refs()
Accenti.update_forward_refs()
BboxLiteral.update_forward_refs()
IntervalLiteral.update_forward_refs()
CharacterExpression.update_forward_refs()
ArrayLiteral.update_forward_refs()
ArrayExpression.update_forward_refs()
