<img src="assets/badge.svg" alt="Logo" width="200">

# bovidae-ta

Farm and cattle domain definitions created by the [Bovi-Analytics Lab](https://bovi-analytics.org/).

## Install

```bash
pip install -e .
```

Or add to a `uv` project with:

```bash
uv add /path/to/bovidae-ta
```

After making local changes to the library, update the installation in a `uv` project with:

```bash
uv pip install /path/to/bovidae-ta --reinstall
```

## Quick Start

```python
from datetime import datetime, timezone
from uuid import uuid4

from bovidaeta import (
    AnimalGender,
    BirthMetadata,
    Cow,
    Event,
    EventType,
    Herd,
)

cow_id = uuid4()
herd_id = uuid4()

cow = Cow(
    animal_id=cow_id,
    herd_id=herd_id,
    gender=AnimalGender.FEMALE,
    birth_date=datetime(2020, 1, 1).date(),
)
herd = Herd(herd_id=herd_id)

# Direct model construction.
event = Event(
    event_id=uuid4(),
    event_type=EventType.BIRTH,
    animal_id=cow_id,
    datetime=datetime.now(timezone.utc),
)

# Typed metadata payload + direct Event construction.
birth_metadata = BirthMetadata(calving_ease_type=None, parturition_birth_status_type=None)
birth_event = Event(
    event_id=uuid4(),
    event_type=EventType.BIRTH,
    animal_id=cow_id,
    datetime=datetime.now(timezone.utc),
    metadata=birth_metadata.model_dump(exclude_none=False),
)
```

## Repository layout

```
src/bovidaeta/
├── cow.py, herd.py, event.py, event_metadata.py, enums.py   domain models
├── io/          DairyData, and one backend per store
├── schemas/     the DDL for both backends, shipped with the package
└── simulation/  generates a dummy farm database to work against
examples/        runnable walkthroughs, one per backend
pipelines/       SQLite -> Delta load job
```

## Loading data

`DairyData` is the only loader. The same events are stored two ways, and
one class reads both:

```python
from bovidaeta import DairyData, EventType

# On a farm: one farm's SQLite database, on a local edge device.
data = DairyData.from_sqlite("dairy_farm.db")

# In Databricks: every farm, in Unity Catalog, for research.
data = DairyData.from_delta("cornell_catalog.cornell_schema")

# Identical from here on.
df = data.load_events(subset_events=[EventType.MILK_RECORDING])
```

The arguments are the same either way. The **return type is not**:
`from_sqlite` gives a polars `DataFrame`, `from_delta` a Spark one,
because that is what each environment wants to work in. Swapping the
constructor starts a port of an analysis script rather than finishing it.

`from_delta` needs Spark: already present inside a Databricks notebook,
otherwise `pip install 'bovidaeta[delta]'`.

See [`src/bovidaeta/io/README.md`](src/bovidaeta/io/README.md) for the
filters and the places the two stores differ, and [`examples/`](examples)
for runnable walkthroughs of each.

## Building a wheel

To install the library on a Databricks cluster, build a wheel and upload
it to a Unity Catalog volume:

```bash
uv build --wheel          # -> dist/bovidaeta-0.1.0-py3-none-any.whl
databricks fs cp dist/bovidaeta-0.1.0-py3-none-any.whl \
    dbfs:/Volumes/cornell_catalog/cornell_schema/libs/
```

Then, in the notebook:

```python
%pip install /Volumes/cornell_catalog/cornell_schema/libs/bovidaeta-0.1.0-py3-none-any.whl
%restart_python
```

Bump `version` in `pyproject.toml` when you re-upload — pip will not
reinstall over a version it already has, so an unchanged version number
leaves the cluster running the old code.

## Model Reference

- `Cow`: Animal identity, pedigree, and lifecycle record.
- `Herd`: Herd identity and location metadata.
- `Event`: Timeline event envelope with `event_type`, `datetime`, and `metadata`.
- `Event metadata models`: Typed metadata contracts for constructing `Event.metadata` payloads.
- `Lactation`: Pending (not yet implemented/exported).
