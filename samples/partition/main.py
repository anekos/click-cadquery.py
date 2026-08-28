import cadquery as cq
from pydantic import Field, model_validator

from click_cadquery import BuildParam, define_app
from click_cadquery.git import version_number as ver
from click_cadquery.partition import (
    PartitionExpr,
    PartitionParam,
    partition_field,
    walls_solid,
)

# Shell- and glob-unsafe characters of partition expressions, mapped for filenames.
FILENAME_SAFE = str.maketrans({"*": "@", ",": "+", "(": "[", ")": "]", ":": "="})


# PartitionParam supplies the partition field, layout() (solved inside the
# inner rectangle) and the does-it-fit validation.
class BoxParam(BuildParam, PartitionParam):
    width: float = Field(default=120.0, description="Outer width of the box")
    depth: float = Field(default=80.0, description="Outer depth of the box")
    height: float = Field(default=40.0, description="Outer height (the top is open)")
    thickness: float = Field(
        default=2.0, description="Wall, floor and divider thickness"
    )
    partition: PartitionExpr = partition_field("2x3")

    @property
    def inner_width(self) -> float:
        return self.width - 2 * self.thickness

    @property
    def inner_depth(self) -> float:
        return self.depth - 2 * self.thickness

    @property
    def inner_height(self) -> float:
        return self.height - self.thickness

    @model_validator(mode="after")
    def walls_must_fit(self) -> "BoxParam":
        if min(self.inner_width, self.inner_depth, self.inner_height) <= 0:
            raise ValueError("the walls do not fit into the outer size")
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
