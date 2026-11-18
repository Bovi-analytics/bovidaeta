# Loading data

Bovidaeta provides a simple `DairyData` class to efficiently load dairy data
in Python, so you don't need to write SQL queries.

Currently we support loading bovidaeta stored in two contexts:

```python
from bovidaeta import DairyData, EventType

data = DairyData.from_sqlite("dairy_farm.db")

data = DairyData.from_delta("bovidaeta.farms")

# Identical from here on.
df = data.load_events(subset_events=[EventType.MILK_RECORDING])
```

More details on the difference between `from_sqlite` and `from_delta`:

|          | `from_sqlite`                                     | `from_delta`                                |
| -------- | ------------------------------------------------- | ------------------------------------------- |
| Store    | SQLite file, one per farm                         | Delta tables in Unity Catalog               |
| Scope    | one farm                                          | every farm                                  |
| Location | local, on your own device or a farm's edge device | Databricks                                  |
| Returns  | polars `DataFrame`                                | Spark `DataFrame`                           |
| Schema   | [`schemas/sqlite.sql`](../schemas/sqlite.sql)     | [`schemas/delta.sql`](../schemas/delta.sql) |
| Needs    | nothing beyond the package                        | pyspark (`pip install 'bovidaeta[delta]'`)  |

Runnable walkthroughs live in [`examples/`](../../../examples).

## Return types

`load_events` returns **polars** from a SQLite source and a **Spark
DataFrame** from Delta, because these are most efficient for local and Databricks processing respectively.
You can switch between these and other packages like _pandas_ with just one command (e.g. `.to_pandas()`).

If you want to **switch loading methods** (for example if you first develop locally with SQLite data before moving to Databricks), you will need to change the processing logic slightly. For example: `df.height` becomes `df.count()`,
`group_by` becomes `groupBy`, and polars expressions become Spark ones.

When a Delta result is small enough to fit on the driver, `to_polars` is optional so you can switch to polars-shaped code, making later migrations easier:

```python
from bovidaeta import to_polars

data = DairyData.from_delta("bovidaeta.farms")

per_cow = data.load_events(...).groupBy("animal_id").avg("milking_yield")
df = to_polars(per_cow)  # aggregate first; this collects
# now you can use polars-style code
```

## Filtering

`load_events` takes six optional filters, all combining with AND:

- `dts_start` / `dts_end` — restrict to a datetime range (inclusive)
- `subset_events` — only these `EventType`s
- `subset_metadata` — give these top-level metadata keys as columns,
  instead of returning the raw `metadata` blob
- `subset_cows` — only these `animal_id`s
- `subset_herds` — only cows in these `herd_id`s

Every event row comes back with `event_id`, `animal_id`, `event_type`,
`datetime`, and then either `metadata` or one column per requested key.

**Use the filters where possible.** They can dramatically decrease the amount of data read and save a lot of waiting time. Especially the local SQLite files can quickly blow up when data is moved from SQLite into a DataFrame, so not using filters can easily create memory problems.

```python
from datetime import datetime, timezone

df = data.load_events(
    dts_start=datetime(2020, 1, 1, tzinfo=timezone.utc),
    dts_end=datetime(2021, 1, 1, tzinfo=timezone.utc),
    subset_events=[EventType.MILK_RECORDING],
    subset_metadata={"milking_yield": "DOUBLE"},
)
```

`subset_metadata` accepts either an iterable of keys or a `{key: type}`
mapping. The cast matters on Delta, where metadata is stored as `VARIANT`
and will not aggregate until it is cast; on SQLite `json_extract` is
untyped and polars infers the column type, so the mapping is accepted and
applied but rarely needed. Writing it either way works against both.

## Nested metadata

Only _top-level_ keys can be requested. Metadata that nests (for example
`DiagnosisMetadata.disease`, which stores `{"disease": {"disease_code":
...}}`) should be requested by its top-level key and unnested afterwards:

```python
# polars, from_sqlite
df = data.load_events(subset_events=[EventType.DIAGNOSIS], subset_metadata=["disease"])
df = df.with_columns(
    pl.col("disease")
    .map_elements(lambda s: json.loads(s)["disease_code"], return_dtype=pl.Utf8)
    .alias("disease_code")
)

# Spark, from_delta
df = df.withColumn("disease_code", F.expr("disease:disease_code::STRING"))
```

`schemas/delta.sql` also defines views (`milk_recording_v`,
`diagnosis_v`) that have already unnested the common event types.
