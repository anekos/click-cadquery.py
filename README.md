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
```

This automatically creates a CLI with the following options:

```bash
python main.py build --width 150 --height 80 --depth 50 --name my-case --show
python main.py build --width 150 --height 80 --depth 50 --name my-case --screenshot
```

## API Reference

### `define_app(Param: type[BuildParam], build: Callable[[Param], cq.Workplane]) -> click.Group`

Builds a complete single-command CLI (as used in the Quick Start above): a
`build` command generated from `Param`'s fields, wired to `build`, with
export to `dist/` plus `--show`/`--screenshot` handled automatically.

**Parameters:**
- `Param`: A `BuildParam` subclass whose fields become CLI options
- `build`: Function that takes a `Param` instance and returns a `cq.Workplane`

### `BuildParam`

Base class for `define_app`/`define_build_command` parameter models.
Subclasses must implement a `filename` property, used as the default export
filename under `dist/` when no output path is given on the command line.

### `define_build_command(group: click.Group, Param: type[BuildParam], build: Callable[[Param], cq.Workplane], name: str = "build")`

Lower-level building block behind `define_app`: attaches a single build
command to an existing `click.Group` instead of creating a new one. Useful
when combining a `define_app`-style command with other manually defined
commands on the same CLI (see `samples/multi`, which composes multiple
commands by hand with `define_options` directly).

### `define_options(klass: type[BaseModel])`

Decorator that automatically generates Click options from a Pydantic model.
This is what `define_build_command`/`define_app` use internally; use it
directly for manually composed multi-command CLIs (see `samples/multi`).

**Parameters:**
- `klass`: A Pydantic BaseModel class whose fields will be converted to CLI options

**Generated CLI signature:**
- Each model field becomes a `--field-name` option
- Field types are preserved for Click type validation
- `X | None` fields are parsed as `X`; omitting the option yields `None`
- Field defaults and descriptions are used for CLI help
- Automatically adds `output` argument for file output
- Automatically adds `--show` flag for showing results
- Automatically adds `--screenshot` flag for saving a screenshot next to the
  output file (`<output>.png`)

**Function signature requirements:**
The decorated function must accept:
- `param`: Instance of the Pydantic model with parsed CLI values
- `output`: Optional Path for output file
- `show`: Boolean flag for showing results
- `screenshot`: Boolean flag for saving a screenshot

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
