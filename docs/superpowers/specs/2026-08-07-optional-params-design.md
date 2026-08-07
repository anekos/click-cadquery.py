# Optional (`X | None`) パラメタ対応

2026-08-07

## 目的

`define_options` が `X | None` アノテーションの Pydantic フィールドを受け付け、
「未指定なら `None`、指定したら `X` として解釈」される click オプションを生成する。

現状は `assert isinstance(anot, type)` で落ちるため Optional フィールドは使えない。

## 仕様

- 対応するのは基本形のみ: `X | None`(`X` は `int` / `float` / `str` などの単純型)。
  `types.UnionType`(`X | None` 記法)と `typing.Union`(`Optional[X]` 記法)の両方を検出する。
- Union の引数から `NoneType` を除いてちょうど 1 つの単純型(`isinstance(x, type)`)が
  残る場合のみサポートし、内側の型を unwrap して既存の処理に流す。
- `Literal[...] | None` や `int | str` などの複合 Union は、明示的なメッセージ付きの
  `TypeError` を送出する(裸の assert failure より親切にする)。
- 生成される click.option は既存の非 Optional フィールドと同一形で、
  `type=` に内側の型、`default=` に `field_data.default`(通常 `None`)が渡るだけ。
  - 未指定 → モデルに `None` が入る
  - `--label foo` → `str` として解釈され `"foo"` が入る
  - `default=None` のとき click は `[default: ...]` を表示しないので `--help` も自然
- CLI から明示的に `None` を渡す手段は設けない(未指定 = `None`)。

## 実装方針

`src/click_cadquery/__init__.py` の `define_options` のフィールドループに
unwrap 処理を追加する(15 行程度)。Literal 判定の後、`assert isinstance(anot, type)`
の前に Union を検出・検証する。

## sample / README

- sample の `BoxParam` に Optional フィールドを 1 つ追加して実演する
  (`label: str | None = Field(default=None, ...)`、指定時のみ filename に含める)。
- README の Quick Start は従来どおり sample/main.py と完全同期する。

## テスト

書かない(ユーザ判断)。sample の CLI 実行(`--help`、未指定/指定の両ケース)で
動作確認する。
