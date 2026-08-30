import functools
import json
import shlex
import sys
import tomllib
import types
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeVar

import cadquery as cq
import click
from cadquery import vis
from click.core import ParameterSource
from pydantic import BaseModel, ValidationError

TypePath = click.types.Path(path_type=Path)
TypeExistingFile = click.types.Path(exists=True, dir_okay=False, path_type=Path)
T = TypeVar("T", bound=BaseModel)

# (param, output, show, screenshot)
CommandFunction = Callable[[T, Path | None, bool, bool], None]


def define_options(klass: type[BaseModel]):  # type: ignore
    """
    Decorator to build a command function with click.option
    """

    def decorator(fn: CommandFunction):  # type: ignore
        def decorated(
            output: Path | None, show: bool, screenshot: bool, **kwargs: Any
        ) -> None:
            return fn(  # type: ignore
                param=klass(**kwargs), output=output, show=show, screenshot=screenshot
            )

        decorated = click.argument("output", type=TypePath, required=False)(decorated)
        decorated = click.option(
            "--show", is_flag=True, help="Show the result in a viewer"
        )(decorated)
        decorated = click.option(
            "--screenshot",
            is_flag=True,
            help="Save a screenshot next to the output file (<output>.png)",
        )(decorated)

        return _add_param_options(decorated, klass)

    return decorator


def _add_param_options(
    decorated: Callable[..., None], klass: type[BaseModel]
) -> Callable[..., None]:
    """Attach one click.option per model field to `decorated`, plus a
    `--json` option that reads defaults from a previous build's JSON dump
    (options given explicitly on the command line still win)."""
    inner = decorated

    # functools.wraps carries over click params already attached to `inner`
    # (e.g. output/--show/--screenshot in define_options)
    @functools.wraps(inner)
    def with_json_defaults(json_file: Path | None, **kwargs: Any) -> None:
        if json_file is not None:
            ctx = click.get_current_context()
            for name, value in _read_param_json(json_file, klass).items():
                if ctx.get_parameter_source(name) is ParameterSource.DEFAULT:
                    kwargs[name] = value
        return inner(**kwargs)

    decorated = click.option(
        "--json",
        "json_file",
        type=TypeExistingFile,
        help="Read defaults from a previous build's JSON dump (explicit options win)",
    )(with_json_defaults)

    for field_name, field_data in klass.model_fields.items():
        anot = field_data.annotation

        if typing.get_origin(anot) is Literal:
            decorated = click.option(
                _to_option_name(field_name),
                type=click.Choice(list(typing.get_args(anot))),
                default=field_data.default,
                help=field_data.description,
            )(decorated)
            continue

        # `X | None` — unwrap to X; unset options fall back to the None default
        anot, _ = _unwrap_optional(field_name, anot)

        assert isinstance(anot, type)

        # e.g. @click.option("--width", type=float, default=100.0)
        decorated = click.option(
            _to_option_name(field_name),
            type=anot,
            default=field_data.default,
            help=field_data.description,
        )(decorated)

    return decorated


def _read_param_json(json_path: Path, klass: type[BaseModel]) -> dict[str, Any]:
    """Field values from a previous build's JSON dump; keys that are not
    fields of `klass` are ignored."""
    data = json.loads(json_path.read_text())
    if not isinstance(data, dict):
        raise click.UsageError(f"{json_path}: expected a JSON object of parameters")
    return {name: data[name] for name in klass.model_fields if name in data}


class BuildParam(BaseModel):
    @property
    def filename(self) -> str:
        raise NotImplementedError


TP = TypeVar("TP", bound=BuildParam)


def define_build_command(
    group: click.Group,
    Param: type[TP],
    build: Callable[[TP], cq.Workplane | cq.Assembly],
    name: str = "build",
):
    @group.command(name=name)
    @define_options(Param)
    def command_build(
        output: Path | None, param: TP, show: bool, screenshot: bool
    ) -> None:
        _build_and_export(build, param, output, show, screenshot)


def define_interactive_command(
    group: click.Group,
    Param: type[TP],
    build: Callable[[TP], cq.Workplane | cq.Assembly],
    name: str = "interactive",
):
    @group.command(name=name)
    @click.argument("output", type=TypePath, required=False)
    @click.option("--show", is_flag=True, help="Show the result in a viewer")
    @click.option(
        "--screenshot",
        is_flag=True,
        help="Save a screenshot next to the output file (<output>.png)",
    )
    @click.option(
        "--json",
        "json_file",
        type=TypeExistingFile,
        help="Read prompt defaults from a previous build's JSON dump",
    )
    def command_interactive(
        output: Path | None, show: bool, screenshot: bool, json_file: Path | None
    ) -> None:
        overrides = _read_param_json(json_file, Param) if json_file else {}
        param = _prompt_param(Param, overrides)
        _build_and_export(build, param, output, show, screenshot)


def define_preview_command(
    group: click.Group,
    Param: type[TP],
    preview: Callable[[TP], str],
    name: str = "preview",
):
    """A command taking the same param options as `build` that prints
    `preview(param)` instead of building — e.g. a partition layout diagram."""

    def command_preview(**kwargs: Any) -> None:
        click.echo(preview(Param(**kwargs)))

    group.command(name=name)(_add_param_options(command_preview, Param))


def define_info_command(
    group: click.Group,
    Param: type[TP],
    build: Callable[[TP], cq.Workplane | cq.Assembly],
    name: str = "info",
):
    """A command for project-viewer tooling: writes a JSON description of
    `Param`'s fields (plus the project title/description from `pyproject.toml`
    when present) to OUTPUT, and a screenshot of `build(Param())` (all
    defaults) next to it as OUTPUT with a `.png` suffix."""

    @group.command(name=name)
    @click.argument("output", type=TypePath, required=False)
    def command_info(output: Path | None) -> None:
        info_path = output if output else Path("dist") / ".project.json"
        info_path.parent.mkdir(parents=True, exist_ok=True)
        image_path = info_path.with_suffix(".png")

        param = Param()
        model_path = info_path.with_suffix(Path(param.filename).suffix)
        info_path.write_text(json.dumps(_model_info(Param), indent=2))

        result = build(param)
        result.export(str(model_path))
        vis.show(result, interact=False, screenshot=str(image_path))


def define_app(
    Param: type[TP],
    build: Callable[[TP], cq.Workplane | cq.Assembly],
) -> click.Group:
    @click.group(context_settings={"show_default": True})
    @click.pass_context
    def main(ctx: click.Context) -> None:
        # ctx.obj = App()
        pass

    define_build_command(main, Param, build)
    define_interactive_command(main, Param, build)
    define_info_command(main, Param, build)
    _define_partition_preview(main, Param)

    return main


def _model_info(Param: type[TP]) -> dict[str, Any]:
    """Project-viewer JSON: title/description from `pyproject.toml` (cwd)
    when present, the default export filename, and a schema entry per
    field."""
    info: dict[str, Any] = dict(_project_meta(Path.cwd()))
    info["filename"] = Param().filename
    info["params"] = [
        _field_info(name, field_data) for name, field_data in Param.model_fields.items()
    ]
    return info


def _project_meta(directory: Path) -> dict[str, Any]:
    """`{"title": ..., "description": ...}` from `directory/pyproject.toml`'s
    `[project]` table; keys are omitted when absent, `{}` when there is no
    pyproject.toml."""
    pyproject = directory / "pyproject.toml"
    if not pyproject.is_file():
        return {}

    project = tomllib.loads(pyproject.read_text()).get("project", {})
    meta = {}
    if "name" in project:
        meta["title"] = project["name"]
    if "description" in project:
        meta["description"] = project["description"]
    return meta


def _field_info(field_name: str, field_data: Any) -> dict[str, Any]:
    """`{"name", "type", "default", "description"?, "choices"? | "optional"?}`
    for one `Param` field — the same type-unwrapping `_add_param_options`
    uses to build CLI options."""
    anot = field_data.annotation
    entry: dict[str, Any] = {"name": field_name}

    if typing.get_origin(anot) is Literal:
        choices = typing.get_args(anot)
        entry["type"] = type(choices[0]).__name__
        entry["default"] = field_data.default
        if field_data.description:
            entry["description"] = field_data.description
        entry["choices"] = list(choices)
        return entry

    anot, optional = _unwrap_optional(field_name, anot)
    entry["type"] = anot.__name__
    entry["default"] = field_data.default
    if field_data.description:
        entry["description"] = field_data.description
    if optional:
        entry["optional"] = True
    return entry


def _define_partition_preview(group: click.Group, Param: type[TP]) -> None:
    """Auto-register a `partition` preview command when `Param` carries a
    PartitionExpr field.

    The layout comes from `Param.layout()` when defined; otherwise it is
    built from the single PartitionExpr field and the conventional
    `inner_width` / `inner_depth` / `thickness` attributes, centred on the
    origin. Params providing neither convention are left alone — register a
    preview yourself with define_preview_command.
    """
    from . import partition

    fields = partition.partition_fields(Param)
    if not fields:
        return

    def has(name: str) -> bool:
        return name in Param.model_fields or hasattr(Param, name)

    layout_of: Callable[[TP], partition.Layout]
    if callable(getattr(Param, "layout", None)):

        def layout_of(param: TP) -> partition.Layout:
            return param.layout()  # type: ignore[attr-defined]
    elif len(fields) == 1 and all(
        has(name) for name in ("inner_width", "inner_depth", "thickness")
    ):
        field_name = fields[0]

        def layout_of(param: TP) -> partition.Layout:
            width: float = param.inner_width  # type: ignore[attr-defined]
            depth: float = param.inner_depth  # type: ignore[attr-defined]
            thickness: float = param.thickness  # type: ignore[attr-defined]
            return partition.solve(
                partition.parse(getattr(param, field_name)),
                partition.Rect(-width / 2, -depth / 2, width, depth),
                thickness,
            )
    else:
        return

    define_preview_command(
        group,
        Param,
        lambda param: partition.preview_text(layout_of(param)),
        name="partition",
    )


def _build_and_export(
    build: Callable[[TP], cq.Workplane | cq.Assembly],
    param: TP,
    output: Path | None,
    show: bool,
    screenshot: bool,
) -> None:
    print(_format_annotated_params(param), file=sys.stderr)
    print(file=sys.stderr)
    print("Build with:", file=sys.stderr)
    print(_format_command_line(param), file=sys.stderr)

    result = build(param)

    dist = Path("dist")
    dist.mkdir(exist_ok=True)
    export_path = output if output else dist / param.filename
    _export(result, param, export_path, show, screenshot)

    print("Write to:", file=sys.stderr)
    # path on stdout with no trailing newline, so it pastes cleanly into a
    # clipboard; flush before the stderr newline below, since stdout without
    # a newline stays buffered and would otherwise print after it
    print(export_path.resolve(), end="")
    sys.stdout.flush()
    print(file=sys.stderr)


def _export(
    result: cq.Workplane | cq.Assembly,
    param: BuildParam,
    export_path: Path,
    show: bool,
    screenshot: bool,
) -> None:
    result.export(str(export_path))
    export_path.with_suffix(".json").write_text(param.model_dump_json(indent=2))
    if screenshot:
        vis.show(result, interact=False, screenshot=f"{export_path}.png")
    if show:
        vis.show(result)


def _format_annotated_params(param: BuildParam) -> str:
    """`name = value  # description`, columns aligned across all fields."""
    fields = type(param).model_fields
    values = {name: repr(getattr(param, name)) for name in fields}
    name_width = max(len(name) for name in fields)
    value_width = max(len(value) for value in values.values())

    lines = []
    for name, field_data in fields.items():
        line = f"{name.ljust(name_width)} = {values[name].ljust(value_width)}"
        if field_data.description:
            line += f"  # {field_data.description}"
        else:
            line = line.rstrip()
        lines.append(line)
    return "\n".join(lines)


def _format_command_line(param: BuildParam) -> str:
    """CLI flags reproducing `param`, quoted only where the shell requires it."""
    parts = []
    for field_name, value in param.model_dump().items():
        if value is None:
            continue
        parts.append(_to_option_name(field_name))
        parts.append(shlex.quote(str(value)))
    return " ".join(parts)


def _unwrap_optional(field_name: str, annotation: Any) -> tuple[Any, bool]:
    """`X | None` — unwrap to `(X, True)`; anything else is `(annotation, False)`."""
    if typing.get_origin(annotation) in (types.UnionType, typing.Union):
        inners = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(inners) != 1 or not isinstance(inners[0], type):
            raise TypeError(
                f"Unsupported annotation for field {field_name!r}: {annotation!r}"
                " (only `X | None` with a simple type X is supported)"
            )
        return inners[0], True
    return annotation, False


def _prompt_for_field(field_name: str, field_data: Any, current: Any) -> Any:
    anot = field_data.annotation
    label = field_data.description or field_name

    if typing.get_origin(anot) is Literal:
        choices = [str(c) for c in typing.get_args(anot)]
        return click.prompt(label, default=str(current), type=click.Choice(choices))

    anot, optional = _unwrap_optional(field_name, anot)

    if anot is bool:
        return click.confirm(label, default=bool(current))

    if optional:
        raw = click.prompt(
            label, default="" if current is None else str(current), show_default=True
        )
        return None if raw == "" else anot(raw)

    return click.prompt(label, default=current, type=anot)


def _prompt_param(Param: type[TP], overrides: dict[str, Any] | None = None) -> TP:
    fields = Param.model_fields
    values: dict[str, Any] = {
        name: (overrides or {}).get(name, data.default) for name, data in fields.items()
    }
    pending = list(fields.keys())

    while True:
        for name in pending:
            values[name] = _prompt_for_field(name, fields[name], values[name])

        try:
            return Param(**values)
        except ValidationError as e:
            errors = e.errors()
            click.echo(click.style("Invalid input:", fg="red"), err=True)
            for err in errors:
                loc = ".".join(str(part) for part in err["loc"]) or "(all fields)"
                click.echo(f"  {loc}: {err['msg']}", err=True)

            field_errors = {err["loc"][0] for err in errors if err["loc"]}
            if any(not err["loc"] for err in errors):
                pending = list(fields.keys())
            else:
                pending = [name for name in fields if name in field_errors]


def _to_option_name(field_name: str) -> str:
    return f"--{field_name.replace('_', '-')}"
