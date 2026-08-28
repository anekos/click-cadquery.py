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

from typing import Any, Self

from pydantic import BaseModel, GetCoreSchemaHandler
from pydantic_core import core_schema

from .geometry import walls_solid
from .model import Axis, Cell, Layout, PartitionError, Rect, Spec, Wall
from .parser import parse
from .render import describe, preview_text, render_ascii
from .solver import solve


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


def partition_fields(Param: type[BaseModel]) -> list[str]:
    """Names of `Param` fields declared as PartitionExpr."""
    return [
        name
        for name, field in Param.model_fields.items()
        if isinstance(field.annotation, type)
        and issubclass(field.annotation, PartitionExpr)
    ]


__all__ = [
    "Axis",
    "Cell",
    "Layout",
    "PartitionError",
    "PartitionExpr",
    "Rect",
    "Spec",
    "Wall",
    "describe",
    "parse",
    "partition_fields",
    "preview_text",
    "render_ascii",
    "solve",
    "walls_solid",
]
