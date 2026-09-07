import json

import cadquery as cq
import pytest
from click.testing import CliRunner

from click_cadquery import BuildParam, define_app


class Param(BuildParam):
    width: float = 100.0
    count: int = 2
    offset: float | None = None

    @property
    def filename(self) -> str:
        return "test.stl"


def build(param: Param) -> cq.Workplane:
    return cq.Workplane("XY").box(1, 1, 1)


@pytest.fixture
def app():
    return define_app(Param, build)


def _built_params(app, tmp_path, *options):
    out = tmp_path / "out.stl"
    result = CliRunner().invoke(app, ["build", str(out), *options])
    assert result.exit_code == 0, result.output
    return json.loads(out.with_suffix(".json").read_text())


def test_plain_numbers_still_work(app, tmp_path):
    params = _built_params(app, tmp_path, "--width", "42", "--count", "3")
    assert params["width"] == 42.0
    assert params["count"] == 3


def test_float_option_accepts_arithmetic(app, tmp_path):
    params = _built_params(app, tmp_path, "--width", "100/2+5")
    assert params["width"] == 55.0


def test_parentheses_and_unary_minus(app, tmp_path):
    params = _built_params(app, tmp_path, "--width", "-(25+4)*-2")
    assert params["width"] == 58.0


def test_int_option_accepts_arithmetic_with_whole_result(app, tmp_path):
    params = _built_params(app, tmp_path, "--count", "6/2")
    assert params["count"] == 3


def test_optional_float_accepts_arithmetic(app, tmp_path):
    params = _built_params(app, tmp_path, "--offset", "1/4")
    assert params["offset"] == 0.25


def test_int_option_rejects_fractional_result(app, tmp_path):
    result = CliRunner().invoke(app, ["build", "--count", "7/2"])
    assert result.exit_code != 0
    assert "not an integer" in result.output


def test_division_by_zero_is_rejected(app, tmp_path):
    result = CliRunner().invoke(app, ["build", "--width", "1/0"])
    assert result.exit_code != 0
    assert "division by zero" in result.output


def test_power_is_supported(app, tmp_path):
    params = _built_params(app, tmp_path, "--width", "2**10")
    assert params["width"] == 1024.0


@pytest.mark.parametrize(
    "expression",
    [
        "width+1",  # names
        "__import__('os')",  # calls
        "1+",  # syntax error
        "'12'",  # non-numeric result
        "9**9**9**9",  # simpleeval's power guard
    ],
)
def test_non_arithmetic_input_is_rejected(app, expression):
    result = CliRunner().invoke(app, ["build", "--width", expression])
    assert result.exit_code != 0


def test_interactive_prompt_accepts_arithmetic(app, tmp_path):
    out = tmp_path / "out.stl"
    # width = 100/4, count and offset keep their defaults
    result = CliRunner().invoke(app, ["interactive", str(out)], input="100/4\n\n\n")
    assert result.exit_code == 0, result.output
    assert json.loads(out.with_suffix(".json").read_text())["width"] == 25.0
