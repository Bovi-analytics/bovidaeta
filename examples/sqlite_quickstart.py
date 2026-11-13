# %% [markdown]
# # Working with one farm's events (SQLite)
#
# `DairyData.from_sqlite` reads a single farm's `.db` file.
# Use this when you want to test locally or write code that will run
# on edge devices.
#
# Use data from a real farm, or get simulated data with:
# `python -m bovidaeta.simulation`
#
# BEFORE running this script, change the `DATA_PATH` to point to
# your data.
#
# This is a percent-format script: run it top to bottom with
# `python examples/sqlite_quickstart.py`, or open it as a notebook.

# %%
import json
from datetime import datetime, timezone

import polars as pl

from bovidaeta import DairyData, EventType

DATA_PATH = "dairy_farm.db"

data = DairyData.from_sqlite(DATA_PATH)
print(data)

# %% [markdown]
# ## 1. Simple counts

# %%
df = data.load_events()
print(f"{df.height:,} events total")
print(df.group_by("event_type").len().sort("len", descending=True))

# %% [markdown]
# ## 2. Filtering
#
# By using the filters we only read and load relevant data from the file.
# This is MUCH more efficient than first loading all data and then filtering
# in Python.

# %%
milk = data.load_events(
    subset_events=[EventType.MILK_RECORDING],
    subset_metadata=["milking_yield"],
)
print(milk.head())
print(f"{milk.height:,} milk recordings")

# %% [markdown]
# `dts_start` / `dts_end` narrow by time:

# %%
milk_2020 = data.load_events(
    dts_start=datetime(2020, 1, 1, tzinfo=timezone.utc),
    dts_end=datetime(2021, 1, 1, tzinfo=timezone.utc),
    subset_events=[EventType.MILK_RECORDING],
    subset_metadata=["milking_yield"],
)
print(f"{milk_2020.height:,} milk recordings in 2020")

# %% [markdown]
# `subset_cows` narrows to specific animals — how you would pull one cow's
# timeline:

# %%
some_cow = milk["animal_id"][0]
timeline = data.load_events(subset_cows=[some_cow])
print(f"{timeline.height:,} events for cow {some_cow}")
print(timeline.group_by("event_type").len().sort("len", descending=True))

# %% [markdown]
# ## 3. Nested metadata
#
# `subset_metadata` extracts *top-level* keys only. Some metadata models
# nest, for example `DiagnosisMetadata` stores `{"disease": {"disease_code": ...}}`.
# Ask for the top-level key and unnest afterwards.

# %%
diag = data.load_events(
    subset_events=[EventType.DIAGNOSIS],
    subset_metadata=["disease"],
)
diag = diag.with_columns(
    pl.col("disease")
    .map_elements(lambda s: json.loads(s)["disease_code"], return_dtype=pl.Utf8)
    .alias("disease_code")
)
print(diag.group_by("disease_code").len().sort("len", descending=True))

# %% [markdown]
# ## 4. Example question: does mastitis cost milk?
#
# This is just to show how to work with the bovidaeta through polars, it's not a
# proper scientific analysis, so take the results with a big grain of salt!

# %%
per_cow = milk.group_by("animal_id").agg(
    pl.col("milking_yield").mean().alias("avg_daily_yield")
)

mastitis_cows = (
    diag.filter(pl.col("disease_code") == "MAS")["animal_id"].unique().to_list()
)
with_mastitis = per_cow.filter(pl.col("animal_id").is_in(mastitis_cows))
without_mastitis = per_cow.filter(~pl.col("animal_id").is_in(mastitis_cows))

print(
    f"avg daily yield, WITH mastitis diagnosis:    "
    f"{with_mastitis['avg_daily_yield'].mean():.1f} kg  (n={with_mastitis.height:,})"
)
print(
    f"avg daily yield, WITHOUT mastitis diagnosis: "
    f"{without_mastitis['avg_daily_yield'].mean():.1f} kg  (n={without_mastitis.height:,})"
)

# %% [markdown]
# ## 5. Cows and herds

# %%
cows = data.load_cows()
print(f"{cows.height:,} cows")
print(cows.head(3))

herds = data.load_herds()
print(herds)

# %% [markdown]
# ## 6. Optional: Converting to other frames

# %%
# pandas is not a dependency of this package, so
# install it separately if that is the frame you want.
try:
    print(per_cow.to_pandas().head())
except ModuleNotFoundError:
    print("pandas not installed - `pip install pandas` to use .to_pandas()")
