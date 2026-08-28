"""Text rendering of a solved Layout, for CLI confirmation."""

from __future__ import annotations

from collections.abc import Callable

from .model import Layout, Rect


def describe(layout: Layout) -> str:
    """One line per cell: index (matching `render_ascii`), size and position."""
    lines = []
    for i, cell in enumerate(layout.cells, 1):
        lines.append(
            f"[{i}] {_fmt(cell.w)} x {_fmt(cell.d)} mm"
            f"  (x {_fmt(cell.x)}..{_fmt(cell.x + cell.w)},"
            f" y {_fmt(cell.y)}..{_fmt(cell.y + cell.d)})"
        )
    return "\n".join(lines)


def preview_text(layout: Layout) -> str:
    """Diagram plus per-cell sizes — the standard CLI confirmation output."""
    return f"{render_ascii(layout)}\n\n{describe(layout)}"


def render_ascii(layout: Layout, width: int = 48) -> str:
    """Top view of the layout, `width` characters wide inside the border.

    Y grows away from the viewer: the first text row is the far (+Y) side.
    Cells are labelled with their `describe` index where there is room.
    """
    rect = layout.rect
    columns = max(width, 2)
    # Terminal characters are roughly twice as tall as wide.
    rows = max(2, round(columns * (rect.d / rect.w) * 0.5))

    def to_col(x: float) -> int:
        return 1 + round((x - rect.x) / rect.w * (columns - 1))

    def to_row(y: float) -> int:
        return 1 + round((rect.y + rect.d - y) / rect.d * (rows - 1))

    canvas = [[" "] * (columns + 2) for _ in range(rows + 2)]
    for col in range(columns + 2):
        canvas[0][col] = canvas[rows + 1][col] = "-"
    for row in range(rows + 2):
        canvas[row][0] = canvas[row][columns + 1] = "|"
    for row, col in ((0, 0), (0, columns + 1), (rows + 1, 0), (rows + 1, columns + 1)):
        canvas[row][col] = "+"

    for wall in layout.walls:
        if wall.axis == "x":
            col = to_col(wall.pos)
            for row in range(to_row(wall.hi), to_row(wall.lo) + 1):
                canvas[row][col] = "+" if canvas[row][col] in "-+" else "|"
        else:
            row = to_row(wall.pos)
            for col in range(to_col(wall.lo), to_col(wall.hi) + 1):
                canvas[row][col] = "+" if canvas[row][col] in "|+" else "-"

    # Junctions: a second pass, so that a wall end meeting a wall drawn later
    # still becomes "+".
    for wall in layout.walls:
        if wall.axis == "x":
            col = to_col(wall.pos)
            ends = ((to_row(wall.hi) - 1, col), (to_row(wall.lo) + 1, col))
        else:
            row = to_row(wall.pos)
            ends = ((row, to_col(wall.lo) - 1), (row, to_col(wall.hi) + 1))
        for row, col in ends:
            if canvas[row][col] != " ":
                canvas[row][col] = "+"

    for i, cell in enumerate(layout.cells, 1):
        _place_label(canvas, str(i), cell, to_col, to_row)

    return "\n".join("".join(row).rstrip() for row in canvas)


def _place_label(
    canvas: list[list[str]],
    text: str,
    cell: Rect,
    to_col: Callable[[float], int],
    to_row: Callable[[float], int],
) -> None:
    row = to_row(cell.y + cell.d / 2)
    start = to_col(cell.x + cell.w / 2) - len(text) // 2
    if start < 0 or start + len(text) > len(canvas[row]):
        return
    if any(canvas[row][start + k] != " " for k in range(len(text))):
        return
    for k, char in enumerate(text):
        canvas[row][start + k] = char


def _fmt(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
