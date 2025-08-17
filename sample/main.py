from pathlib import Path

import cadquery as cq
import cadquery.vis as vis
import click
from click_cadquery import define_options
from click_cadquery.git import version_number as ver
from pydantic import BaseModel

TypePath = click.types.Path(path_type=Path)


class Param(BaseModel):
    width: int = 100
    height: int = 100
    depth: int = 100
    thickness: float = 2.0

    @property
    def filename(self) -> str:
        return f"v{ver()}-{self.width}w{self.height}h{self.depth}d{self.thickness}t.stl"


@click.group(context_settings={"show_default": True})
@click.pass_context
def main(ctx: click.Context) -> None:
    pass


@main.command(name="build")
@define_options(Param)
def command_build(output: Path | None, param: Param, show: bool) -> None:
    print("Build with:", param)

    result = build(param)

    dist = Path("dist")
    dist.mkdir(exist_ok=True)
    result.export(str(output if output else dist / param.filename))
    if show:
        vis.show(result, axes=True, axes_length=10)


def build(param: Param) -> cq.Workplane:
    result = cq.Workplane("XY")

    result = result.box(
        length=param.depth,
        height=param.height,
        width=param.width,
    )

    result = result.faces(">Z").shell(param.thickness, kind="intersection")

    fillet = param.thickness / 2
    result = result.edges("|Z").fillet(fillet)

    return result


if __name__ == "__main__":
    main()
