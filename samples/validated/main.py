import re

import cadquery as cq
import click
from pydantic import Field, ValidationError, field_validator, model_validator

from click_cadquery import BuildParam, define_app
from click_cadquery.git import version_number as ver

NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_ASPECT_RATIO = 10


class BoxParam(BuildParam):
    width: int = Field(default=100, gt=0, le=1000, description="Outer width of the box")
    height: int = Field(
        default=100, gt=0, le=1000, description="Outer height of the box"
    )
    depth: int = Field(default=100, gt=0, le=1000, description="Outer depth of the box")
    name: str = Field(default="my-box", description="Base name of the output file")

    @field_validator("name")
    @classmethod
    def name_must_be_filesystem_safe(cls, value: str) -> str:
        if not NAME_PATTERN.match(value):
            raise ValueError(
                f"must contain only letters, digits, '-' and '_' (got {value!r})"
            )
        return value

    @model_validator(mode="after")
    def dimensions_must_not_be_too_thin(self) -> "BoxParam":
        smallest = min(self.width, self.height, self.depth)
        largest = max(self.width, self.height, self.depth)
        if largest > smallest * MAX_ASPECT_RATIO:
            raise ValueError(
                "width/height/depth are too disproportionate"
                f" (ratio {largest / smallest:.1f} exceeds {MAX_ASPECT_RATIO})"
            )
        return self

    @property
    def filename(self) -> str:
        return f"{self.name}-v{ver()}-{self.width}w{self.height}h{self.depth}d.stl"


def build_box(param: BoxParam) -> cq.Workplane:
    return cq.Workplane("XY").box(param.depth, param.width, param.height)


main = define_app(BoxParam, build_box)


def _format_validation_error(error: ValidationError) -> str:
    lines = [f"Invalid parameters ({error.error_count()} error(s)):"]
    for err in error.errors():
        loc = ".".join(str(part) for part in err["loc"]) or "(all fields)"
        lines.append(f"  {loc}: {err['msg']}")
    return "\n".join(lines)


if __name__ == "__main__":
    try:
        main()
    except ValidationError as e:
        error = click.ClickException(_format_validation_error(e))
        error.show()
        raise SystemExit(error.exit_code) from None
