# click-cadquery

[![PyPI version](https://badge.fury.io/py/click-cadquery.svg)](https://badge.fury.io/py/click-cadquery)
[![Python Versions](https://img.shields.io/pypi/pyversions/click-cadquery.svg)](https://pypi.org/project/click-cadquery/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Click decorators for CadQuery CLI applications with automatic option generation from Pydantic models.

## Overview

This library provides utilities to build command-line interfaces for CadQuery applications using Click. It automatically generates CLI options from Pydantic model fields, making it easy to create parametric CAD scripts with type-safe command-line interfaces.

## Features

- **Automatic CLI generation**: Convert Pydantic models to Click options automatically
- **Type safety**: Leverage Pydantic's type validation for CLI parameters
- **CadQuery integration**: Built-in support for output files and viewer integration
- **Git utilities**: Helper functions for version tracking

## Installation

```bash
pip install click-cadquery
```

## Quick Start

```python
from pathlib import Path
from typing import Literal

import cadquery as cq
import click
from cadquery import vis
from pydantic import BaseModel, Field

from click_cadquery import define_options
from click_cadquery.git import version_number as ver


class BoxParam(BaseModel):
    width: int = Field(default=100, description="Outer width of the box")
    height: int = Field(default=100, description="Outer height of the box")
    depth: int = Field(default=100, description="Outer depth of the box")
    thickness: float = Field(default=2.0, description="Wall thickness")
    corner_radius: float = Field(
        default=1.0, description="Fillet radius of vertical edges"
    )
    name: str = Field(default="my-box", description="Base name of the output file")
    label: str | None = Field(
        default=None, description="Extra label appended to the name"
    )
    part: Literal["case", "cover", "box"] = Field(
        default="box", description="Part to build"
    )

    @property
    def filename(self) -> str:
        label = "" if self.label is None else f"-{self.label}"
        return f"{self.name}{label}-v{ver()}-{self.part}-{self.width}w{self.height}h{self.depth}d{self.thickness}t.stl"


class CylinderParam(BaseModel):
    radius: float = Field(default=30.0, description="Radius of the cylinder")
    height: float = Field(default=50.0, description="Height of the cylinder")
    name: str = Field(default="my-cylinder", description="Base name of the output file")

    @property
    def filename(self) -> str:
        return f"{self.name}-v{ver()}-{self.radius}r{self.height}h.stl"


@click.group(context_settings={"show_default": True})
@click.pass_context
def main(ctx: click.Context) -> None:
    pass


@main.command(name="build")
@define_options(BoxParam)
def command_build(output: Path | None, param: BoxParam, show: bool) -> None:
    print("Build with:", param)
    export(build_box(param), param.filename, output, show)


@main.command(name="cylinder")
@define_options(CylinderParam)
def command_cylinder(output: Path | None, param: CylinderParam, show: bool) -> None:
    print("Build with:", param)
    export(build_cylinder(param), param.filename, output, show)


def build_box(param: BoxParam) -> cq.Workplane:
    result = cq.Workplane("XY")

    result = result.box(
        length=param.depth,
        height=param.height,
        width=param.width,
    )

    result = result.faces(">Z").shell(param.thickness, kind="intersection")

    result = result.edges("|Z").fillet(param.corner_radius)

    return result


def build_cylinder(param: CylinderParam) -> cq.Workplane:
    return cq.Workplane("XY").cylinder(param.height, param.radius)


def export(
    result: cq.Workplane, filename: str, output: Path | None, show: bool
) -> None:
    dist = Path("dist")
    dist.mkdir(exist_ok=True)
    result.export(str(output if output else dist / filename))
    if show:
        vis.show(result, axes=True, axes_length=10)


if __name__ == "__main__":
    main()
```

This automatically creates a CLI with the following options:

```bash
python main.py build --width 150 --height 80 --depth 50 --thickness 3.0 --corner-radius 2 --part case --name my-case --show
python main.py cylinder --radius 20 --height 40 --show
```

## API Reference

### `define_options(klass: type[BaseModel])`

Decorator that automatically generates Click options from a Pydantic model.

**Parameters:**
- `klass`: A Pydantic BaseModel class whose fields will be converted to CLI options

**Generated CLI signature:**
- Each model field becomes a `--field-name` option
- Field types are preserved for Click type validation
- `X | None` fields are parsed as `X`; omitting the option yields `None`
- Field defaults and descriptions are used for CLI help
- Automatically adds `output` argument for file output
- Automatically adds `--show` flag for showing results

**Function signature requirements:**
The decorated function must accept:
- `param`: Instance of the Pydantic model with parsed CLI values
- `output`: Optional Path for output file
- `show`: Boolean flag for showing results

### Git Utilities

#### `version_number() -> int`

Returns the number of commits in the current git repository.

```python
from click_cadquery.git import version_number

version = version_number()
print(f"Build version: {version}")
```

## Requirements

- Python >= 3.11
- Click >= 8.2.1
- Pydantic >= 2.11.7

## License

MIT License - see LICENSE file for details.
