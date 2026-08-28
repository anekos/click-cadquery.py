"""Recursive-descent parser for partition expressions.

Grammar (whitespace is free):

    spec  := INT                    # lone integer: that many equal cells
           | INT "x" INT           # grid: columns x rows of equal cells
           | unit (":" unit)+      # ratio: bare numbers are weights
           | unit ("," unit)*      # list: bare numbers are millimetres
    unit  := size ("(" spec ")")?  # "(...)" splits the cell along the other axis
    size  := NUM | NUM "*" | "*"   # "*" is a weight (defaults to 1)
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Cell, PartitionError, Spec

_TOKEN = re.compile(r"\s*(?:(?P<num>\d+(?:\.\d+)?|\.\d+)|(?P<sym>[,*:()x]))")


@dataclass(frozen=True)
class _Token:
    kind: str  # "num" or the symbol itself
    value: float
    pos: int


@dataclass(frozen=True)
class _Unit:
    """A parsed unit whose bare number is not yet mm or weight."""

    num: float | None
    star: bool
    child: Spec | None
    pos: int


def parse(text: str) -> Spec:
    """Parse a partition expression, raising PartitionError on invalid input."""
    tokens = _tokenize(text)
    spec, i = _parse_spec(tokens, 0, text)
    if i != len(tokens):
        raise _error(text, tokens[i].pos, f"unexpected {tokens[i].kind!r}")
    return spec


def _tokenize(text: str) -> list[_Token]:
    tokens: list[_Token] = []
    i = 0
    while i < len(text):
        m = _TOKEN.match(text, i)
        if not m:
            if text[i:].strip():
                raise _error(text, i, f"unexpected character {text[i:].strip()[0]!r}")
            break
        if m.group("num") is not None:
            tokens.append(_Token("num", float(m.group("num")), m.start("num")))
        else:
            tokens.append(_Token(m.group("sym"), 0.0, m.start("sym")))
        i = m.end()
    if not tokens:
        raise PartitionError("empty partition expression")
    return tokens


def _parse_spec(tokens: list[_Token], i: int, text: str) -> tuple[Spec, int]:
    first, i = _parse_unit(tokens, i, text)
    kind = tokens[i].kind if i < len(tokens) else None

    if kind == "x":
        return _parse_grid(first, tokens, i, text)

    if kind in (",", ":"):
        units = [first]
        while i < len(tokens) and tokens[i].kind in (",", ":"):
            if tokens[i].kind != kind:
                raise _error(
                    text, tokens[i].pos, "cannot mix ',' and ':' at the same level"
                )
            unit, i = _parse_unit(tokens, i + 1, text)
            units.append(unit)
        as_mm = kind == ","
        return Spec(tuple(_to_cell(u, as_mm, text) for u in units)), i

    # A single unit: a bare integer is a count of equal cells.
    if first.num is not None and not first.star and first.child is None:
        count = _to_count(first.num, first.pos, text)
        return Spec((Cell(weight=1.0),) * count), i
    return Spec((_to_cell(first, as_mm=True, text=text),)), i


def _parse_grid(
    first: _Unit, tokens: list[_Token], i: int, text: str
) -> tuple[Spec, int]:
    if first.num is None or first.star or first.child is not None:
        raise _error(text, tokens[i].pos, "grid 'NxM' takes plain integers")
    columns = _to_count(first.num, first.pos, text)
    i += 1
    if i >= len(tokens) or tokens[i].kind != "num":
        raise _error(text, _end_pos(tokens, i, text), "expected a row count after 'x'")
    rows = _to_count(tokens[i].value, tokens[i].pos, text)
    row_spec = Spec((Cell(weight=1.0),) * rows)
    return Spec((Cell(weight=1.0, child=row_spec),) * columns), i + 1


def _parse_unit(tokens: list[_Token], i: int, text: str) -> tuple[_Unit, int]:
    if i >= len(tokens):
        raise _error(text, _end_pos(tokens, i, text), "expected a number or '*'")
    token = tokens[i]

    num: float | None = None
    star = False
    if token.kind == "num":
        if token.value <= 0:
            raise _error(text, token.pos, "sizes and weights must be positive")
        num = token.value
        i += 1
        if i < len(tokens) and tokens[i].kind == "*":
            star = True
            i += 1
    elif token.kind == "*":
        star = True
        i += 1
    else:
        raise _error(text, token.pos, f"expected a number or '*', got {token.kind!r}")

    child: Spec | None = None
    if i < len(tokens) and tokens[i].kind == "(":
        child, i = _parse_spec(tokens, i + 1, text)
        if i >= len(tokens) or tokens[i].kind != ")":
            raise _error(text, _end_pos(tokens, i, text), "expected ')'")
        i += 1

    return _Unit(num, star, child, token.pos), i


def _to_cell(unit: _Unit, as_mm: bool, text: str) -> Cell:
    if unit.star:
        return Cell(weight=unit.num if unit.num is not None else 1.0, child=unit.child)
    assert unit.num is not None
    if as_mm:
        return Cell(mm=unit.num, child=unit.child)
    return Cell(weight=unit.num, child=unit.child)


def _to_count(value: float, pos: int, text: str) -> int:
    if value != int(value) or value < 1:
        raise _error(text, pos, "a cell count must be a positive integer")
    return int(value)


def _end_pos(tokens: list[_Token], i: int, text: str) -> int:
    return tokens[i].pos if i < len(tokens) else len(text)


def _error(text: str, pos: int, message: str) -> PartitionError:
    return PartitionError(f"{message} (column {pos + 1} of {text!r})")
