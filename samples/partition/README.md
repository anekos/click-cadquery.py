# partition sample

An open-top box whose dividers are described by a partition expression
(`click_cadquery.partition`). See the library README for the syntax.
The `partition` preview subcommand is registered automatically by
`define_app` because the model carries a `PartitionExpr` field.

```console
$ make add_library            # install click-cadquery into the venv
$ make preview                # print the layout diagram for '30(3),*'
$ make build                  # export dist/partitioned-box-....stl
$ uv run main.py partition --partition '1:2:1' --width 150
$ uv run main.py build --partition '20,*,2*'
```
