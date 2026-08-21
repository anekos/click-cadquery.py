import types
import typing
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, TypeVar

import cadquery as cq
import click
from cadquery import vis
from pydantic import BaseModel

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
            if typing.get_origin(anot) in (types.UnionType, typing.Union):
                inners = [a for a in typing.get_args(anot) if a is not type(None)]
                if len(inners) != 1 or not isinstance(inners[0], type):
                    raise TypeError(
                        f"Unsupported annotation for field {field_name!r}: {anot!r}"
                        " (only `X | None` with a simple type X is supported)"
                    )
                anot = inners[0]

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
        result.export(str(export_path))
        if screenshot:
            vis.show(result, interact=False, screenshot=f"{export_path}.png")
        if show:
            vis.show(result)


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

    return main


def _to_option_name(field_name: str) -> str:
    return f"--{field_name.replace('_', '-')}"
