# Working with events data

Event timelines are stored in a SQLite database with two tables, `Cows` and
`Events` (see `src/simulation/main.py` for the schema). Use the `FarmData`
class to load events from that database into a polars `DataFrame`.

```python
from bovidaeta import FarmData

fd = FarmData(db_path="dairy_farm_134000.db")

df = fd.load_events()
print(f"{df.height:,} events total")
print(df.group_by("event_type").len().sort("len", descending=True))
```

## Filtering

`load_events` takes five optional filters, all of which can be combined:

- `dts_start` / `dts_end` - restrict to events in a datetime range
- `subset_events` - only load specific `EventType`s
- `subset_metadata` - only pull specific top-level metadata keys as columns,
  instead of the raw `metadata` JSON column
- `subset_cows` - only load events for specific `animal_id`s

It is recommended to use these filters where possible, to decrease data loading time and memory footprint.

```python
from datetime import datetime, timezone

import polars as pl
from bovidaeta import EventType, FarmData

fd = FarmData(db_path="dairy_farm_134000.db")

cows_of_interest = ["1839fd28-a74a-5b4d-9096-aee03cad1b1c", "ceef5f18-6f4d-57f4-b7f8-0ab79626f815"]
dts_start = datetime(2020, 1, 1, tzinfo=timezone.utc)
dts_end = datetime(2021, 1, 1, tzinfo=timezone.utc)

df = fd.load_events(
    dts_start=dts_start,
    dts_end=dts_end,
    subset_events=[EventType.MILK_RECORDING],
    subset_metadata=["milking_yield"],
    subset_cows=cows_of_interest,
)

per_cow = df.group_by("animal_id").agg(pl.col("milking_yield").mean())
print(per_cow)
```

Note: `subset_metadata` only extracts top-level keys. Metadata that is
nested (for example `DiagnosisMetadata.disease`, which stores
`{"disease": {"disease_code": ..., ...}}`) needs to be requested by its
top-level key and unnested afterwards:

```python
import json

import polars as pl

diag = fd.load_events(subset_events=[EventType.DIAGNOSIS], subset_metadata=["disease"])
diag = diag.with_columns(
    pl.col("disease")
    .map_elements(lambda s: json.loads(s)["disease_code"], return_dtype=pl.Utf8)
    .alias("disease_code")
)
print(diag.group_by("disease_code").len().sort("len", descending=True))
```

## A slightly bigger example

Comparing milk yield for cows with and without a mastitis diagnosis:

```python
milk = fd.load_events(subset_events=[EventType.MILK_RECORDING], subset_metadata=["milking_yield"])
per_cow = milk.group_by("animal_id").agg(pl.col("milking_yield").mean().alias("avg_daily_yield"))

mastitis_cows = diag.filter(pl.col("disease_code") == "MAS")["animal_id"].unique().to_list()
with_mastitis = per_cow.filter(pl.col("animal_id").is_in(mastitis_cows))
without_mastitis = per_cow.filter(~pl.col("animal_id").is_in(mastitis_cows))

print(f"avg daily yield, WITH mastitis diagnosis:    {with_mastitis['avg_daily_yield'].mean():.1f} kg")
print(f"avg daily yield, WITHOUT mastitis diagnosis: {without_mastitis['avg_daily_yield'].mean():.1f} kg")
```

This `DataFrame` can easily be converted to other formats:

## Pandas

Convert to Pandas DataFrame:

```python
df_pandas = df.to_pandas()
```

## PySpark

Use the `sparkpl` package to convert to PySpark:

```python
from sparkpl.converter import polars_to_spark
df_spark = polars_to_spark(df)
```
