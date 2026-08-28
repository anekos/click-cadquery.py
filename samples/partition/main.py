import cadquery as cq
from pydantic import Field, model_validator

from click_cadquery import BuildParam, define_app
from click_cadquery.git import version_number as ver
from click_cadquery.partition import (
    Layout,
    PartitionError,
    PartitionExpr,
    Rect,
    parse,
    solve,
    walls_solid,
)

# Shell- and glob-unsafe characters of partition expressions, mapped for filenames.
FILENAME_SAFE = str.maketrans({"*": "@", ",": "+", "(": "[", ")": "]", ":": "="})


class BoxParam(BuildParam):
    width: float = Field(default=120.0, description="Outer width of the box")
    depth: float = Field(default=80.0, description="Outer depth of the box")
    height: float = Field(default=40.0, description="Outer height (the top is open)")
    thickness: float = Field(
        default=2.0, description="Wall, floor and divider thickness"
    )
    partition: PartitionExpr = Field(
        default=PartitionExpr("2x3"),
        description="Divider layout: N | NxM | '30,40,*' | '1:2:1' | '30(3),*'",
    )

    @property
    def inner_width(self) -> float:
        return self.width - 2 * self.thickness

    @property
    def inner_depth(self) -> float:
        return self.depth - 2 * self.thickness

    @property
    def inner_height(self) -> float:
        return self.height - self.thickness

    def layout(self) -> Layout:
        return solve(
            parse(self.partition),
            Rect(
                -self.inner_width / 2,
                -self.inner_depth / 2,
                self.inner_width,
                self.inner_depth,
            ),
            self.thickness,
        )

    @model_validator(mode="after")
    def partition_must_fit(self) -> "BoxParam":
        if min(self.inner_width, self.inner_depth, self.inner_height) <= 0:
            raise ValueError("the walls do not fit into the outer size")
        try:
            self.layout()
        except PartitionError as e:
            raise ValueError(f"the partition does not fit: {e}") from e
        return self

    @property
    def filename(self) -> str:
        return (
            f"partitioned-box-v{ver()}"
            f"-{self.width:g}w{self.height:g}h{self.depth:g}d"
            f"-{self.partition.translate(FILENAME_SAFE)}div"
            ".stl"
        )


def build_box(param: BoxParam) -> cq.Workplane:
    result = (
        cq.Workplane("XY")
        .box(param.width, param.depth, param.height, centered=(True, True, False))
        .faces(">Z")
        .shell(-param.thickness)
    )

    walls = walls_solid(param.layout(), param.inner_height)
    if walls is not None:
        result = result.union(walls.translate((0, 0, param.thickness)))

    return result


# define_app registers the `partition` preview subcommand automatically,
# since BoxParam carries a PartitionExpr field and a layout() method.
main = define_app(BoxParam, build_box)


if __name__ == "__main__":
    main()
