import pytest

from click_cadquery.partition import Rect, parse, solve, walls_solid


def test_no_walls_returns_none():
    layout = solve(parse("1"), Rect(0.0, 0.0, 100.0, 60.0), 2.0)
    assert walls_solid(layout, height=30.0) is None


def test_single_wall_volume_and_bbox():
    layout = solve(parse("2"), Rect(-50.0, -30.0, 100.0, 60.0), 2.0)
    solid = walls_solid(layout, height=30.0)
    assert solid is not None
    shape = solid.val()
    # Overlap defaults to thickness / 2, so the wall spans 60 + 2 mm along Y.
    assert shape.Volume() == pytest.approx(2.0 * 62.0 * 30.0)
    bbox = shape.BoundingBox()
    assert bbox.xlen == pytest.approx(2.0)
    assert bbox.ylen == pytest.approx(62.0)
    assert bbox.zlen == pytest.approx(30.0)
    assert bbox.zmin == pytest.approx(0.0)


def test_crossing_walls_form_one_solid():
    layout = solve(parse("2x2"), Rect(-41.0, -41.0, 82.0, 82.0), 2.0)
    solid = walls_solid(layout, height=20.0)
    assert solid is not None
    assert len(solid.solids().vals()) == 1
    # One full-depth wall plus two half-span walls, minus their overlaps with
    # the vertical wall (each horizontal wall reaches t/2 = 1 mm into it).
    vertical = 2.0 * 84.0 * 20.0
    horizontal = 2 * (2.0 * 42.0 * 20.0)
    overlap = 2 * (1.0 * 2.0 * 20.0)
    assert solid.val().Volume() == pytest.approx(vertical + horizontal - overlap)
