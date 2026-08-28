from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Axis = Literal["x", "y"]


class PartitionError(ValueError):
    """Invalid partition expression, or a layout that does not fit."""


@dataclass(frozen=True)
class Cell:
    """One cell of a Spec: a fixed size in mm, or a weight sharing the rest."""

    mm: float | None = None
    weight: float | None = None
    child: Spec | None = None
    """Splits this cell further, along the axis perpendicular to the parent's."""


@dataclass(frozen=True)
class Spec:
    """Parsed partition expression: cells laid out along one axis."""

    cells: tuple[Cell, ...]


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle on the XY plane; (x, y) is the min corner."""

    x: float
    y: float
    w: float
    d: float


@dataclass(frozen=True)
class Wall:
    """A divider wall.

    axis="x" means the wall is perpendicular to X, centred at x=pos and
    spanning y in [lo, hi]; axis="y" is the transposed case.
    """

    axis: Axis
    pos: float
    lo: float
    hi: float


@dataclass(frozen=True)
class Layout:
    """Solved layout: the leaf cells and divider walls inside `rect`."""

    rect: Rect
    thickness: float
    cells: tuple[Rect, ...]
    walls: tuple[Wall, ...]
