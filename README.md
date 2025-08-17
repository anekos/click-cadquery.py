# click-cadquery

[![PyPI version](https://badge.fury.io/py/click-cadquery.svg)](https://badge.fury.io/py/click-cadquery)
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

import cadquery as cq
import cadquery.vis as vis
import click
from click_cadquery import define_options
from click_cadquery.git import version_number as ver
from pydantic import BaseModel

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
```

This automatically creates a CLI with the following options:

```bash
python main.py build --width 150 --height 80 --depth 50 --thickness 3.0 --show
```

## API Reference

### `define_options(klass: type[BaseModel])`

Decorator that automatically generates Click options from a Pydantic model.

**Parameters:**
- `klass`: A Pydantic BaseModel class whose fields will be converted to CLI options

**Generated CLI signature:**
- Each model field becomes a `--field-name` option
- Field types are preserved for Click type validation
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
