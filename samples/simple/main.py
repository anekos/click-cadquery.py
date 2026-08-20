import cadquery as cq
from pydantic import Field

from click_cadquery import BuildParam, define_app
from click_cadquery.git import version_number as ver


class BoxParam(BuildParam):
    width: int = Field(default=100, description="Outer width of the box")
    height: int = Field(default=100, description="Outer height of the box")
    depth: int = Field(default=100, description="Outer depth of the box")
    name: str = Field(default="my-box", description="Base name of the output file")

    @property
    def filename(self) -> str:
        return f"{self.name}-v{ver()}-{self.width}w{self.height}h{self.depth}d.stl"


def build_box(param: BoxParam) -> cq.Workplane:
    return cq.Workplane("XY").box(param.depth, param.width, param.height)


main = define_app(BoxParam, build_box)


if __name__ == "__main__":
    main()
