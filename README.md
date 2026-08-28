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

Builds a complete CLI (as used in the Quick Start above): a `build` command
generated from `Param`'s fields, plus an `interactive` command that prompts
for each field one at a time, both wired to `build`, with export to `dist/`
plus `--show`/`--screenshot` handled automatically. Alongside the exported
file, `Param` is also dumped as JSON next to it (same path, `.json`
extension).

**Parameters:**
- `Param`: A `BuildParam` subclass whose fields become CLI options
- `build`: Function that takes a `Param` instance and returns a `cq.Workplane`

### `BuildParam`

Base class for `define_app`/`define_build_command`/`define_interactive_command`
parameter models. Subclasses must implement a `filename` property, used as
the default export filename under `dist/` when no output path is given on
the command line.

### `define_build_command(group: click.Group, Param: type[BuildParam], build: Callable[[Param], cq.Workplane], name: str = "build")`

Lower-level building block behind `define_app`: attaches a single build
command to an existing `click.Group` instead of creating a new one. Useful
when combining a `define_app`-style command with other manually defined
commands on the same CLI (see `samples/multi`, which composes multiple
commands by hand with `define_options` directly).

### `define_interactive_command(group: click.Group, Param: type[BuildParam], build: Callable[[Param], cq.Workplane], name: str = "interactive")`

Companion to `define_build_command`: attaches an `interactive` command that
prompts for each of `Param`'s fields one at a time instead of reading them
from CLI options. If the collected values fail Pydantic validation, only
the field(s) implicated by the error are re-prompted (a model-level
validation error re-prompts every field, since no single field can be
blamed).

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

### `define_preview_command(group: click.Group, Param: type[BuildParam], preview: Callable[[Param], str], name: str = "preview")`

Adds a command that takes the same param options as `build` but prints
`preview(param)` instead of building anything.

You rarely need to call this yourself: when the model carries a
`PartitionExpr` field, `define_app` registers a `partition` preview command
automatically (see below).

### Partition expressions (`click_cadquery.partition`)

A small language for describing box dividers, so the layout can be passed on
the command line. The top level splits the width (X) axis; each nested
`(...)` splits the perpendicular axis:

| Expression | Meaning |
|---|---|
| `3` | three equal cells |
| `3x2` | a 3 x 2 grid |
| `30,40,*` | 30 mm, 40 mm, then the rest |
| `1:2:1` | split by weights |
| `20,*,2*` | 20 mm fixed, the rest split 1:2 |
| `30(3),*` | a 30 mm column split into 3 rows, plus an undivided column |
| `1:1(1:1(1:1))` | recursive halving |

Bare numbers are millimetres, `N*` (or `*` = `1*`) are weights sharing the
space left after fixed cells and dividers, and a lone integer is a count of
equal cells. Sizes are cell **inner** sizes; a divider of the given thickness
sits between adjacent cells.

The `PartitionParam` mixin gives a model everything at once — the validated
`partition` field, `layout()` solved inside the inner rectangle centred on
the origin, and a validator rejecting params whose partition does not fit.
It only requires `inner_width`, `inner_depth` and `thickness` on the model:

```python
from click_cadquery.partition import (
    PartitionExpr, PartitionParam, partition_field, walls_solid,
)

class Param(BuildParam, PartitionParam):
    partition: PartitionExpr = partition_field("2x3")  # default + canonical help
    ...  # width/depth/thickness fields, inner_* properties

def build(param: Param) -> cq.Workplane:
    walls = walls_solid(param.layout(), height)  # None when there are no dividers
    ...
```

`partition_field(default)` is a `pydantic.Field` carrying the syntax summary
(`SYNTAX`) as the option help, so the description follows the library when
the language grows; the default is validated at import time.

The lower-level pieces behind the mixin:

- `parse(text) -> Spec` parses an expression (raising `PartitionError`).
- `solve(spec, rect, thickness) -> Layout` computes leaf cells and divider
  walls inside the inner rectangle `rect`.
- `walls_solid(layout, height) -> cq.Workplane | None` builds the dividers as
  one solid sitting on Z=0; each wall end is extended by `thickness / 2` so
  the union with the surrounding shell never merges coincident faces.
- `render_ascii(layout)` / `describe(layout)` draw a top-view diagram and a
  per-cell size listing for CLI confirmation (`preview_text(layout)` combines
  both).

When the model has a `PartitionExpr` field, `define_app` automatically adds a
`partition` subcommand that prints this preview for the given params. The
layout is taken from `Param.layout() -> Layout` when the model defines it;
otherwise it is built from the single `PartitionExpr` field and the
conventional `inner_width` / `inner_depth` / `thickness` attributes, centred
on the origin. Models providing neither convention get no automatic command —
register one yourself with `define_preview_command`.

```console
$ uv run app partition --partition '30(3),*' --width 120
```

Preview a layout against explicit dimensions, without any project:

```console
$ cq-partition '30(3),*' --width 116 --depth 76 --thickness 2
```

(also available as `python -m click_cadquery.partition`).

See `samples/partition` for a complete example: a partitioned open-top box
built on the `PartitionParam` mixin.

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
