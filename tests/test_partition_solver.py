import pytest

from click_cadquery.partition import (
    PartitionError,
    Rect,
    Wall,
    parse,
    solve,
)


def rect(w=100.0, d=60.0):
    return Rect(0.0, 0.0, w, d)


def widths(layout):
    return [pytest.approx(c.w) for c in layout.cells]


def test_equal_split():
    layout = solve(parse("3"), rect(w=100.0), thickness=2.0)
    # available = 100 - 2 * 2 = 96 -> 32 mm each
    assert widths(layout) == [32.0, 32.0, 32.0]
    assert layout.walls == (
        Wall("x", pytest.approx(33.0), 0.0, 60.0),
        Wall("x", pytest.approx(67.0), 0.0, 60.0),
    )


def test_absolute_sizes_with_fill():
    layout = solve(parse("30,40,*"), Rect(0.0, 0.0, 120.0, 60.0), thickness=2.0)
    assert widths(layout) == [30.0, 40.0, 46.0]
    assert [w.pos for w in layout.walls] == [pytest.approx(31.0), pytest.approx(73.0)]


def test_ratio():
    layout = solve(parse("1:2:1"), Rect(0.0, 0.0, 104.0, 60.0), thickness=2.0)
    assert widths(layout) == [25.0, 50.0, 25.0]


def test_nested_wall_spans_only_its_cell():
    layout = solve(parse("30(2),*"), rect(w=100.0, d=60.0), thickness=2.0)
    assert len(layout.cells) == 3
    nested, outer = layout.walls
    # The nested wall splits the 30 mm column along Y and spans only x in 0..30.
    assert nested == Wall("y", pytest.approx(30.0), 0.0, pytest.approx(30.0))
    assert outer == Wall("x", pytest.approx(31.0), 0.0, 60.0)


def test_grid_cells():
    layout = solve(parse("2x3"), Rect(0.0, 0.0, 82.0, 64.0), thickness=2.0)
    assert len(layout.cells) == 6
    assert widths(layout) == [pytest.approx(40.0)] * 6
    assert [pytest.approx(c.d) for c in layout.cells] == [20.0] * 6


def test_offset_rect_is_respected():
    layout = solve(parse("2"), Rect(-50.0, -30.0, 100.0, 60.0), thickness=2.0)
    assert layout.walls == (Wall("x", pytest.approx(0.0), -30.0, 30.0),)


def test_single_cell_has_no_walls():
    layout = solve(parse("1"), rect(), thickness=2.0)
    assert layout.walls == ()
    assert widths(layout) == [100.0]


def test_fixed_sizes_must_sum_to_available():
    with pytest.raises(PartitionError, match="add a '\\*' cell"):
        solve(parse("30,40"), rect(w=100.0), thickness=2.0)


def test_fixed_sizes_exact_sum_is_accepted():
    layout = solve(parse("30,68"), rect(w=100.0), thickness=2.0)
    assert widths(layout) == [30.0, 68.0]


def test_fixed_sizes_leaving_no_room_for_weights():
    with pytest.raises(PartitionError, match="no room left"):
        solve(parse("98,*"), rect(w=100.0), thickness=2.0)


def test_too_many_cells_for_the_span():
    with pytest.raises(PartitionError, match="do not fit"):
        solve(parse("6"), rect(w=10.0), thickness=2.0)


def test_error_names_the_depth_axis_for_nested_specs():
    with pytest.raises(PartitionError, match="depth"):
        solve(parse("*(30,40)"), rect(w=100.0, d=60.0), thickness=2.0)


def test_bad_thickness():
    with pytest.raises(PartitionError, match="thickness"):
        solve(parse("2"), rect(), thickness=0.0)
