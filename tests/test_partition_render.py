from click_cadquery.partition import Rect, describe, parse, render_ascii, solve


def layout(expression, w=100.0, d=60.0, t=2.0):
    return solve(parse(expression), Rect(0.0, 0.0, w, d), t)


def test_describe_lists_each_cell_with_size_and_position():
    text = describe(layout("30,40,*", w=120.0))
    assert text.splitlines() == [
        "[1] 30 x 60 mm  (x 0..30, y 0..60)",
        "[2] 40 x 60 mm  (x 32..72, y 0..60)",
        "[3] 46 x 60 mm  (x 74..120, y 0..60)",
    ]


def test_render_has_a_closed_border():
    lines = render_ascii(layout("1"), width=20).splitlines()
    assert lines[0].startswith("+") and lines[0].rstrip().endswith("+")
    assert lines[-1].startswith("+") and lines[-1].rstrip().endswith("+")
    assert all(line.startswith("|") for line in lines[1:-1])


def test_render_draws_vertical_walls_and_labels():
    text = render_ascii(layout("2"), width=20)
    assert "|" in text.splitlines()[2][1:21]  # strictly inside the border
    assert "1" in text and "2" in text


def test_render_draws_horizontal_walls():
    text = render_ascii(layout("*(2)"), width=20)
    assert any("-" in line for line in text.splitlines()[1:-1])


def test_render_nested_wall_stays_inside_its_cell():
    # "30(2),*": the horizontal wall must not cross the vertical one.
    lines = render_ascii(layout("30(2),*", w=100.0, d=60.0), width=40).splitlines()
    horizontal = next(line for line in lines[1:-1] if "-" in line)
    assert horizontal.index("|", 1) > horizontal.rindex("-")
