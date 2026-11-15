# Pipelines

Jobs that move data between the two storage backends, rather than read
from them. Notebook-format scripts, run in Databricks.

- **`sqlite_to_delta.py`** — reads a volume folder of per-farm
  `dairy_farm_*.db` files and appends their `Herds` / `Cows` / `AnimalEvents`
  rows into the Delta tables. Parameterised by `farms_dir` and
  `catalog_schema` widgets; nothing in it is specific to one dataset.

  Create the tables first by running
  [`bovidaeta/schemas/delta.sql`](../src/bovidaeta/schemas/delta.sql) in a
  SQL editor. The load is a plain append, intended for a first load — an
  incremental one should switch to a `MERGE` on the primary keys.

Once loaded, read the result with `DairyData.from_delta`; see
[`examples/delta_quickstart.py`](../examples/delta_quickstart.py).
