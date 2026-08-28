import cadquery as cq
import pytest
from click.testing import CliRunner

from click_cadquery import BuildParam, define_app
from click_cadquery.partition import (
    PartitionError,
    PartitionExpr,
    Rect,
    parse,
    partition_fields,
    solve,
)


class Param(BuildParam):
    width: float = 100.0
    depth: float = 60.0
    thickness: float = 2.0
    partition: PartitionExpr = PartitionExpr("2")

    @property
    def inner_width(self) -> float:
        return self.width - 2 * self.thickness

    @property
    def inner_depth(self) -> float:
        return self.depth - 2 * self.thickness

    @property
    def filename(self) -> str:
        return "test.stl"


def build(param: Param) -> cq.Workplane:
    return cq.Workplane("XY").box(1, 1, 1)


def test_partition_expr_validates_on_construction():
    assert PartitionExpr("30,*") == "30,*"
    with pytest.raises(PartitionError):
        PartitionExpr("30,")


def test_validated_field_values_are_partition_expr_instances():
    assert isinstance(Param(partition="2").partition, PartitionExpr)


def test_cli_rejects_invalid_expressions_with_the_parse_error():
    app = define_app(Param, build)
    result = CliRunner().invoke(app, ["partition", "--partition", "30,"])
    assert result.exit_code != 0
    assert "expected a number or '*'" in result.output


def test_partition_fields_finds_the_expression_field():
    assert partition_fields(Param) == ["partition"]


def test_partition_fields_ignores_plain_str_fields():
    class NoPartition(BuildParam):
        name: str = "box"
        width: float = 1.0

    assert partition_fields(NoPartition) == []


def test_define_app_auto_registers_a_partition_preview():
    app = define_app(Param, build)
    assert "partition" in app.commands

    result = CliRunner().invoke(app, ["partition", "--partition", "30,*"])
    assert result.exit_code == 0
    # inner 96 x 56 with t=2: 30 mm plus the remaining 64 mm
    assert "[1] 30 x 56 mm" in result.output
    assert "[2] 64 x 56 mm" in result.output


def test_no_preview_without_the_inner_size_convention():
    class Bare(BuildParam):
        partition: PartitionExpr = PartitionExpr("2")

        @property
        def filename(self) -> str:
            return "bare.stl"

    app = define_app(Bare, lambda param: cq.Workplane("XY").box(1, 1, 1))
    assert "partition" not in app.commands


def test_layout_method_takes_precedence_over_the_convention():
    class Custom(Param):
        def layout(self):  # type: ignore[no-untyped-def]
            return solve(parse(self.partition), Rect(0.0, 0.0, 10.0, 10.0), 1.0)

    app = define_app(Custom, build)
    result = CliRunner().invoke(app, ["partition"])
    assert result.exit_code == 0
    # "2" in a 10 mm span with t=1 gives 4.5 mm cells, not the inner_* sizes.
    assert "[1] 4.5 x 10 mm" in result.output


def test_no_preview_without_a_partition_field():
    class Plain(BuildParam):
        width: float = 10.0

        @property
        def filename(self) -> str:
            return "plain.stl"

    app = define_app(Plain, lambda param: cq.Workplane("XY").box(1, 1, 1))
    assert "partition" not in app.commands
