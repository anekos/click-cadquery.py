import json

import cadquery as cq
import pytest
from click.testing import CliRunner

from click_cadquery import BuildParam, define_app
from click_cadquery.partition import PartitionExpr


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


@pytest.fixture
def app():
    return define_app(Param, build)


def test_json_values_replace_the_field_defaults(app, tmp_path):
    params = tmp_path / "params.json"
    params.write_text(json.dumps({"width": 50.0, "depth": 40.0, "thickness": 1.0}))

    result = CliRunner().invoke(app, ["partition", "--json", str(params)])
    assert result.exit_code == 0
    # inner 48 x 38 split in two with t=1: 23.5 mm cells
    assert "[1] 23.5 x 38 mm" in result.output


def test_explicit_options_win_over_json_values(app, tmp_path):
    params = tmp_path / "params.json"
    params.write_text(json.dumps({"width": 50.0, "partition": "3"}))

    result = CliRunner().invoke(
        app, ["partition", "--json", str(params), "--width", "80"]
    )
    assert result.exit_code == 0
    # width 80 (inner 76) from the command line, partition "3" from the JSON
    assert "[3]" in result.output
    assert "[1] 24 x 56 mm" in result.output


def test_unknown_json_keys_are_ignored(app, tmp_path):
    params = tmp_path / "params.json"
    params.write_text(json.dumps({"width": 50.0, "no_such_field": 1}))

    result = CliRunner().invoke(app, ["partition", "--json", str(params)])
    assert result.exit_code == 0


def test_a_non_object_json_file_is_a_usage_error(app, tmp_path):
    params = tmp_path / "params.json"
    params.write_text(json.dumps([1, 2, 3]))

    result = CliRunner().invoke(app, ["partition", "--json", str(params)])
    assert result.exit_code != 0
    assert "expected a JSON object" in result.output


def test_a_missing_json_file_is_rejected_by_click(app, tmp_path):
    result = CliRunner().invoke(
        app, ["partition", "--json", str(tmp_path / "nope.json")]
    )
    assert result.exit_code != 0
    assert "does not exist" in result.output


def test_build_dump_round_trips_through_json(app, tmp_path):
    runner = CliRunner()
    out = tmp_path / "one.stl"
    result = runner.invoke(app, ["build", str(out), "--width", "42"])
    assert result.exit_code == 0
    assert json.loads(out.with_suffix(".json").read_text())["width"] == 42.0

    rebuilt = tmp_path / "two.stl"
    result = runner.invoke(
        app, ["build", str(rebuilt), "--json", str(out.with_suffix(".json"))]
    )
    assert result.exit_code == 0
    assert json.loads(rebuilt.with_suffix(".json").read_text())["width"] == 42.0


def test_interactive_prompt_defaults_come_from_json(app, tmp_path):
    params = tmp_path / "params.json"
    params.write_text(json.dumps({"width": 42.0}))
    out = tmp_path / "out.stl"

    # accept every prompt default by sending empty lines
    result = CliRunner().invoke(
        app, ["interactive", str(out), "--json", str(params)], input="\n\n\n\n"
    )
    assert result.exit_code == 0
    assert "[42.0]" in result.output
    assert json.loads(out.with_suffix(".json").read_text())["width"] == 42.0
