"""Preview a partition expression: `cq-partition` or `python -m click_cadquery.partition`."""

import click

from .model import PartitionError, Rect
from .parser import parse
from .render import describe, render_ascii
from .solver import solve


@click.command(context_settings={"show_default": True})
@click.argument("expression")
@click.option("--width", type=float, default=100.0, help="Inner width (X) in mm")
@click.option("--depth", type=float, default=100.0, help="Inner depth (Y) in mm")
@click.option("--thickness", type=float, default=2.0, help="Divider thickness in mm")
@click.option(
    "--diagram-width", type=int, default=48, help="Diagram width in characters"
)
def main(
    expression: str, width: float, depth: float, thickness: float, diagram_width: int
) -> None:
    """Show how EXPRESSION splits a WIDTH x DEPTH inner area."""
    try:
        layout = solve(parse(expression), Rect(0.0, 0.0, width, depth), thickness)
    except PartitionError as e:
        raise click.ClickException(str(e)) from e
    click.echo(render_ascii(layout, width=diagram_width))
    click.echo()
    click.echo(describe(layout))


if __name__ == "__main__":
    main()
