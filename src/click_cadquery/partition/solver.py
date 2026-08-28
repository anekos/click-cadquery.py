from __future__ import annotations

from .model import Axis, Layout, PartitionError, Rect, Spec, Wall

_EPS = 1e-6

_AXIS_NAME = {"x": "width", "y": "depth"}


def solve(spec: Spec, rect: Rect, thickness: float, axis: Axis = "x") -> Layout:
    """Resolve `spec` inside `rect` (inner sizes, mm) with dividers of `thickness`.

    Cell sizes are inner sizes; a divider of `thickness` sits between adjacent
    cells. Nested specs split their cell along the perpendicular axis.
    """
    if thickness <= 0:
        raise PartitionError("thickness must be positive")
    cells, walls = _solve(spec, rect, thickness, axis)
    return Layout(
        rect=rect, thickness=thickness, cells=tuple(cells), walls=tuple(walls)
    )


def _solve(
    spec: Spec, rect: Rect, thickness: float, axis: Axis
) -> tuple[list[Rect], list[Wall]]:
    cells = spec.cells
    span = rect.w if axis == "x" else rect.d
    available = span - (len(cells) - 1) * thickness
    fixed = sum(c.mm for c in cells if c.mm is not None)
    weights = sum(c.weight for c in cells if c.weight is not None)
    rest = available - fixed

    if available <= _EPS:
        raise PartitionError(
            f"{len(cells)} cells along the {_AXIS_NAME[axis]} do not fit:"
            f" the dividers alone need {(len(cells) - 1) * thickness:g} mm"
            f" of the available {span:g} mm"
        )
    if weights == 0:
        if abs(rest) > _EPS:
            raise PartitionError(
                f"fixed sizes along the {_AXIS_NAME[axis]} sum to {fixed:g} mm"
                f" but {available:g} mm is available; adjust them or add a '*' cell"
            )
    elif rest <= _EPS:
        raise PartitionError(
            f"no room left for '*' cells along the {_AXIS_NAME[axis]}:"
            f" fixed sizes take {fixed:g} mm of the available {available:g} mm"
        )

    leaf_cells: list[Rect] = []
    walls: list[Wall] = []
    cursor = rect.x if axis == "x" else rect.y
    for i, cell in enumerate(cells):
        if cell.mm is not None:
            size = cell.mm
        else:
            assert cell.weight is not None
            size = rest * cell.weight / weights

        if axis == "x":
            cell_rect = Rect(cursor, rect.y, size, rect.d)
        else:
            cell_rect = Rect(rect.x, cursor, rect.w, size)

        if cell.child is not None:
            sub_axis: Axis = "y" if axis == "x" else "x"
            sub_cells, sub_walls = _solve(cell.child, cell_rect, thickness, sub_axis)
            leaf_cells += sub_cells
            walls += sub_walls
        else:
            leaf_cells.append(cell_rect)

        cursor += size
        if i < len(cells) - 1:
            if axis == "x":
                walls.append(Wall("x", cursor + thickness / 2, rect.y, rect.y + rect.d))
            else:
                walls.append(Wall("y", cursor + thickness / 2, rect.x, rect.x + rect.w))
            cursor += thickness

    return leaf_cells, walls
