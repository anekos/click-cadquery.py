"""Divider layout language for storage boxes.

The top level splits the width (X) axis; each nested "(...)" splits the
perpendicular axis:

    3           three equal cells
    3x2         a 3 x 2 grid
    30,40,*     30 mm, 40 mm, then the rest
    1:2:1       split by weights
    20,*,2*     20 mm fixed, the rest split 1:2
    30(3),*     a 30 mm column split into 3 rows, plus an undivided column

Bare numbers are millimetres, "N*" (or "*" = "1*") are weights sharing the
space left after fixed cells and dividers. A lone integer is a count of equal
cells. Sizes are cell inner sizes; a divider of the given thickness sits
between adjacent cells.

Preview a layout from the command line:

    cq-partition '30(3),*' --width 116 --depth 76 --thickness 2
"""

from typing import Any, Self, cast

from pydantic import BaseModel, Field, GetCoreSchemaHandler, model_validator
from pydantic_core import core_schema

from .geometry import walls_solid
from .model import Axis, Cell, Layout, PartitionError, Rect, Spec, Wall
from .parser import parse
from .render import describe, preview_text, render_ascii
from .solver import solve

SYNTAX = "N | NxM | '30,40,*' | '1:2:1' | '30(3),*' (nesting flips the axis)"
"""One-line syntax summary, kept in sync with the parser."""


class PartitionExpr(str):
    """A `str` that must parse as a partition expression.

    Construction validates, so both pydantic fields and click options
    reject invalid expressions with the parser's error message.
    """

    def __new__(cls, value: str) -> Self:
        parse(value)
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls, core_schema.str_schema()
        )


def partition_field(default: str = "1", description: str | None = None) -> Any:
    """A pydantic Field for a PartitionExpr, with the canonical syntax help.

    The default is validated right here, so a typo fails at import time.
    """
    return Field(
        default=PartitionExpr(default),
        description=description or f"Divider layout: {SYNTAX}",
    )


class PartitionParam(BaseModel):
    """Mixin for build params: a `partition` field plus the standard layout.

    The concrete model must provide `inner_width`, `inner_depth` and
    `thickness` (as fields or properties); `layout()` then solves the
    partition inside the inner rectangle centred on the origin, and a
    validator rejects params whose partition does not fit. Override the
    field to change the default: `partition: PartitionExpr =
    partition_field("2x3")`.
    """

    partition: PartitionExpr = partition_field()

    def layout(self) -> Layout:
        # The inner sizes come from the concrete model, as fields or
        # properties; declaring them here would turn them into pydantic
        # fields, so they stay undeclared.
        param = cast(Any, self)
        return solve(
            parse(self.partition),
            Rect(
                -param.inner_width / 2,
                -param.inner_depth / 2,
                param.inner_width,
                param.inner_depth,
            ),
            param.thickness,
        )

    @model_validator(mode="after")
    def _partition_must_fit(self) -> Self:
        try:
            self.layout()
        except PartitionError as e:
            raise ValueError(f"the partition does not fit: {e}") from e
        return self


def partition_fields(Param: type[BaseModel]) -> list[str]:
    """Names of `Param` fields declared as PartitionExpr."""
    return [
        name
        for name, field in Param.model_fields.items()
        if isinstance(field.annotation, type)
        and issubclass(field.annotation, PartitionExpr)
    ]


__all__ = [
    "SYNTAX",
    "Axis",
    "Cell",
    "Layout",
    "PartitionError",
    "PartitionExpr",
    "PartitionParam",
    "Rect",
    "Spec",
    "Wall",
    "describe",
    "parse",
    "partition_field",
    "partition_fields",
    "preview_text",
    "render_ascii",
    "solve",
    "walls_solid",
]
