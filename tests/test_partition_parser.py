import pytest

from click_cadquery.partition import Cell, PartitionError, Spec, parse


def test_lone_integer_is_a_count():
    assert parse("3") == Spec((Cell(weight=1.0),) * 3)


def test_count_of_one_means_no_divider():
    assert parse("1") == Spec((Cell(weight=1.0),))


def test_grid():
    rows = Spec((Cell(weight=1.0),) * 2)
    assert parse("3x2") == Spec((Cell(weight=1.0, child=rows),) * 3)


def test_absolute_list_with_fill():
    assert parse("30,40,*") == Spec((Cell(mm=30.0), Cell(mm=40.0), Cell(weight=1.0)))


def test_ratio():
    assert parse("1:2:1") == Spec(
        (Cell(weight=1.0), Cell(weight=2.0), Cell(weight=1.0))
    )


def test_weighted_star_in_list():
    assert parse("20,*,2*") == Spec((Cell(mm=20.0), Cell(weight=1.0), Cell(weight=2.0)))


def test_nested_child_flips_axis():
    assert parse("30(3),*") == Spec(
        (
            Cell(mm=30.0, child=Spec((Cell(weight=1.0),) * 3)),
            Cell(weight=1.0),
        )
    )


def test_child_on_ratio_item():
    assert parse("1:2(1:1)") == Spec(
        (
            Cell(weight=1.0),
            Cell(weight=2.0, child=Spec((Cell(weight=1.0), Cell(weight=1.0)))),
        )
    )


def test_deep_nesting():
    inner = Spec((Cell(weight=1.0), Cell(weight=1.0)))
    middle = Spec((Cell(weight=1.0), Cell(weight=1.0, child=inner)))
    assert parse("1:1(1:1(1:1))") == Spec(
        (Cell(weight=1.0), Cell(weight=1.0, child=middle))
    )


def test_whitespace_is_free():
    assert parse(" 30 , * ") == parse("30,*")


def test_decimal_weights():
    assert parse("1:1.618") == Spec((Cell(weight=1.0), Cell(weight=1.618)))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "30,",
        ",30",
        "1:2,3",
        "3.5",
        "0",
        "-3",
        "abc",
        "30(",
        "30()",
        "3x2.5",
        "3*x2",
        "*x2",
        "3x",
        "0*",
        "(3)",
    ],
)
def test_invalid_expressions(text):
    with pytest.raises(PartitionError):
        parse(text)
