import json
from pathlib import Path
from typing import Literal

import cadquery as cq
import pytest
from click.testing import CliRunner
from pydantic import Field

from click_cadquery import BuildParam, _model_info, _project_meta, define_app


class Param(BuildParam):
    width: int = Field(default=100, description="Outer width")
    depth: float = 60.0
    material: Literal["pla", "abs"] = "pla"
    label: str | None = None

    @property
    def filename(self) -> str:
        return "test.stl"


def build(param: Param) -> cq.Workplane:
    return cq.Workplane("XY").box(1, 1, 1)


def test_plain_field_reports_name_type_default_and_description():
    info = _model_info(Param)
    width = next(p for p in info["params"] if p["name"] == "width")
    assert width == {
        "name": "width",
        "type": "int",
        "default": 100,
        "description": "Outer width",
    }


def test_field_without_description_omits_it():
    info = _model_info(Param)
    depth = next(p for p in info["params"] if p["name"] == "depth")
    assert depth == {"name": "depth", "type": "float", "default": 60.0}


def test_literal_field_reports_choices():
    info = _model_info(Param)
    material = next(p for p in info["params"] if p["name"] == "material")
    assert material == {
        "name": "material",
        "type": "str",
        "default": "pla",
        "choices": ["pla", "abs"],
    }


def test_optional_field_is_marked_optional():
    info = _model_info(Param)
    label = next(p for p in info["params"] if p["name"] == "label")
    assert label == {
        "name": "label",
        "type": "str",
        "default": None,
        "optional": True,
    }


def test_filename_uses_default_param_values():
    info = _model_info(Param)
    assert info["filename"] == "test.stl"


def test_project_meta_reads_name_and_description_from_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "widget"\ndescription = "A widget"\n'
    )
    assert _project_meta(tmp_path) == {"title": "widget", "description": "A widget"}


def test_project_meta_is_empty_without_a_pyproject(tmp_path):
    assert _project_meta(tmp_path) == {}


def test_model_info_includes_project_title_and_description(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "widget"\ndescription = "A widget"\n'
    )
    monkeypatch.chdir(tmp_path)
    info = _model_info(Param)
    assert info["title"] == "widget"
    assert info["description"] == "A widget"


def test_model_info_omits_title_and_description_without_a_pyproject(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    info = _model_info(Param)
    assert "title" not in info
    assert "description" not in info


@pytest.fixture
def app():
    return define_app(Param, build)


def test_info_command_writes_json_and_screenshot_next_to_it(app, tmp_path, monkeypatch):
    screenshots: list[str] = []
    monkeypatch.setattr(
        "click_cadquery.vis.show",
        lambda result, interact=True, screenshot=None: screenshots.append(screenshot),
    )

    output = tmp_path / "out.json"
    result = CliRunner().invoke(app, ["info", str(output)])

    assert result.exit_code == 0, result.output
    data = json.loads(output.read_text())
    assert data["filename"] == "test.stl"
    assert screenshots == [str(tmp_path / "out.png")]


def test_info_command_exports_the_model_next_to_the_json(app, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "click_cadquery.vis.show",
        lambda result, interact=True, screenshot=None: None,
    )

    output = tmp_path / "out.json"
    result = CliRunner().invoke(app, ["info", str(output)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "out.stl").exists()


def test_info_command_defaults_to_dist_dot_project(app, tmp_path, monkeypatch):
    screenshots: list[str] = []
    monkeypatch.setattr(
        "click_cadquery.vis.show",
        lambda result, interact=True, screenshot=None: screenshots.append(screenshot),
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(app, ["info"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "dist" / ".project.json").exists()
    assert screenshots == [str(Path("dist") / ".project.png")]
