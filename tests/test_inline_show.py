import base64
import io
import os
from pathlib import Path

import cadquery as cq
import pytest
from click.testing import CliRunner
from pydantic import Field

from click_cadquery import BuildParam, _display_kitty_image, define_app


def _frames(output: str) -> list[str]:
    return [f for f in output.split("\x1b\\") if f]


def _control(frame: str) -> str:
    return frame.removeprefix("\x1b_G").split(";", 1)[0]


def _payload(frame: str) -> str:
    return frame.removeprefix("\x1b_G").split(";", 1)[1]


def test_display_kitty_image_starts_with_the_apc_prefix(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"hello")
    out = io.StringIO()

    _display_kitty_image(png, out)

    assert out.getvalue().startswith("\x1b_G")


def test_display_kitty_image_ends_with_the_apc_terminator(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"hello")
    out = io.StringIO()

    _display_kitty_image(png, out)

    assert out.getvalue().endswith("\x1b\\")


def test_display_kitty_image_embeds_the_base64_encoded_file_content(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"hello world")
    out = io.StringIO()

    _display_kitty_image(png, out)

    assert base64.b64encode(b"hello world").decode("ascii") in out.getvalue()


def test_display_kitty_image_single_chunk_is_marked_as_the_last(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"hello")
    out = io.StringIO()

    _display_kitty_image(png, out, columns=80)

    (frame,) = _frames(out.getvalue())
    assert _control(frame) == "a=T,f=100,c=80,m=0"


def test_display_kitty_image_scales_to_the_given_column_count(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"hello")
    out = io.StringIO()

    _display_kitty_image(png, out, columns=40)

    (frame,) = _frames(out.getvalue())
    assert "c=40" in _control(frame)


def test_display_kitty_image_defaults_columns_to_the_terminal_width(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "shutil.get_terminal_size",
        lambda fallback=(80, 24): os.terminal_size((123, 45)),
    )
    png = tmp_path / "x.png"
    png.write_bytes(b"hello")
    out = io.StringIO()

    _display_kitty_image(png, out)

    (frame,) = _frames(out.getvalue())
    assert "c=123" in _control(frame)


def test_display_kitty_image_splits_large_payloads_and_flags_the_last_chunk(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"x" * 10_000)  # base64-encoded length exceeds one 4096 chunk
    out = io.StringIO()

    _display_kitty_image(png, out)

    frames = _frames(out.getvalue())
    assert len(frames) > 1
    assert all(_control(f).endswith("m=1") for f in frames[:-1])
    assert _control(frames[-1]).endswith("m=0")


def test_display_kitty_image_chunk_payloads_concatenate_to_the_full_base64(tmp_path):
    content = b"x" * 10_000
    png = tmp_path / "x.png"
    png.write_bytes(content)
    out = io.StringIO()

    _display_kitty_image(png, out)

    frames = _frames(out.getvalue())
    assert "".join(_payload(f) for f in frames) == base64.b64encode(content).decode(
        "ascii"
    )


class Param(BuildParam):
    width: int = Field(default=100)

    @property
    def filename(self) -> str:
        return "test.stl"


def build(param: Param) -> cq.Workplane:
    return cq.Workplane("XY").box(1, 1, 1)


@pytest.fixture
def app():
    return define_app(Param, build)


@pytest.fixture
def fake_vis_show(monkeypatch):
    """vis.show writes dummy bytes to `screenshot` instead of rendering."""

    def show(result, interact=True, screenshot=None):
        if screenshot:
            Path(screenshot).write_bytes(b"fake-png-bytes")

    monkeypatch.setattr("click_cadquery.vis.show", show)


@pytest.fixture
def captured_displays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "click_cadquery._display_kitty_image",
        lambda path, stream=None: calls.append(path),
    )
    return calls


def test_inline_show_alone_renders_to_a_temp_file_and_deletes_it_after(
    app, tmp_path, fake_vis_show, captured_displays
):
    output = tmp_path / "out.stl"
    result = CliRunner().invoke(app, ["build", str(output), "--inline-show"])

    assert result.exit_code == 0, result.output
    assert len(captured_displays) == 1
    displayed_path = captured_displays[0]
    assert displayed_path != tmp_path / "out.stl.png"
    assert not displayed_path.exists()


def test_inline_show_with_screenshot_reuses_and_keeps_the_persistent_file(
    app, tmp_path, fake_vis_show, captured_displays
):
    output = tmp_path / "out.stl"
    result = CliRunner().invoke(
        app, ["build", str(output), "--screenshot", "--inline-show"]
    )

    assert result.exit_code == 0, result.output
    expected = Path(f"{output}.png")
    assert captured_displays == [expected]
    assert expected.exists()


def test_screenshot_alone_does_not_display_inline(
    app, tmp_path, fake_vis_show, captured_displays
):
    output = tmp_path / "out.stl"
    result = CliRunner().invoke(app, ["build", str(output), "--screenshot"])

    assert result.exit_code == 0, result.output
    assert captured_displays == []


def test_interactive_command_accepts_inline_show(
    app, tmp_path, fake_vis_show, captured_displays
):
    output = tmp_path / "out.stl"
    result = CliRunner().invoke(
        app, ["interactive", str(output), "--inline-show"], input="\n"
    )

    assert result.exit_code == 0, result.output
    assert len(captured_displays) == 1
