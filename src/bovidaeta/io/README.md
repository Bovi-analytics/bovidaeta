# Working with events data

When you have an hive partition containing a timeline of events, you can use the `FarmData` class to get a DataFrame of the data.

```python
from datetime import datetime, timezone

from bovidaeta import FarmData

fd = FarmData()

# Define subsets of data that we want to load
# These are all optional!
events = ["MilkMeterYields"]
metadata_features = ["milking_yield"]
cows_of_interest = ["9abeb415", "e96e5263"]
dts_start = datetime.fromisoformat("2026-04-20").replace(tzinfo=timezone.utc)
dts_end = datetime.fromisoformat("2026-07-20").replace(tzinfo=timezone.utc)

lazy_df = fd.load(
    dts_start=dts_start,
    dts_end=dts_end,
    subset_cows=cows_of_interest,
    subset_events=events,
    subset_metadata=metadata_features,
)

# Converted to a real DataFrame
df = lazy_df.collect()

print(df.head())
```

This DataFrame can easily be converted to other formats:

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
