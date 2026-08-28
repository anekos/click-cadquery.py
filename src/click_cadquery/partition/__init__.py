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

from typing import Annotated

from pydantic import AfterValidator

from .geometry import walls_solid
from .model import Axis, Cell, Layout, PartitionError, Rect, Spec, Wall
from .parser import parse
from .render import describe, render_ascii
from .solver import solve


def _validated(value: str) -> str:
    parse(value)
    return value


PartitionExpr = Annotated[str, AfterValidator(_validated)]
"""A `str` pydantic field type that must parse as a partition expression."""

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
    "render_ascii",
    "solve",
    "walls_solid",
]
