from __future__ import annotations

import cadquery as cq

from .model import Layout


def walls_solid(
    layout: Layout, height: float, overlap: float | None = None
) -> cq.Workplane | None:
    """Union of all divider walls, sitting on Z=0; None when there are no walls.

    Each wall is extended by `overlap` (default thickness / 2) at both ends so
    that the union with the surrounding shell never has to merge coincident
    faces. Translate the result onto the box floor yourself.
    """
    if not layout.walls:
        return None

    thickness = layout.thickness
    extend = thickness / 2 if overlap is None else overlap

    result: cq.Workplane | None = None
    for wall in layout.walls:
        length = wall.hi - wall.lo + 2 * extend
        mid = (wall.lo + wall.hi) / 2
        if wall.axis == "x":
            size = (thickness, length)
            center = (wall.pos, mid)
        else:
            size = (length, thickness)
            center = (mid, wall.pos)
        box = (
            cq.Workplane("XY")
            .box(size[0], size[1], height, centered=(True, True, False))
            .translate((center[0], center[1], 0))
        )
        result = box if result is None else result.union(box)

    return result
