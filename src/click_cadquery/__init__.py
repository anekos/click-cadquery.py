import types
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeVar

import cadquery as cq
import click
from cadquery import vis
from pydantic import BaseModel, ValidationError

TypePath = click.types.Path(path_type=Path)
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

    return decorator


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
        print("Build with:", param)

        result = build(param)

        dist = Path("dist")
        dist.mkdir(exist_ok=True)
        export_path = output if output else dist / param.filename
        _export(result, param, export_path, show, screenshot)


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
    def command_interactive(output: Path | None, show: bool, screenshot: bool) -> None:
        param = _prompt_param(Param)
        print("Build with:", param)

        result = build(param)

        dist = Path("dist")
        dist.mkdir(exist_ok=True)
        export_path = output if output else dist / param.filename
        _export(result, param, export_path, show, screenshot)


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

    return main


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


def _prompt_param(Param: type[TP]) -> TP:
    fields = Param.model_fields
    values: dict[str, Any] = {name: data.default for name, data in fields.items()}
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
