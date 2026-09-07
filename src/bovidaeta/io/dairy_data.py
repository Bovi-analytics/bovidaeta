"""`DairyData` - the single loader for dairy farm event data."""

from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..enums import EventType
from .base import (
    EventBackend,
    normalise_event_types,
    normalise_ids,
    normalise_metadata,
    validate_datetime_range,
)

if TYPE_CHECKING:  # pragma: no cover
    from pyspark.sql import SparkSession


class DairyData:
    """Load events, cows and herds, from whichever store they live in.

    The same data is kept two ways, and one class reads both:

    ```python
    from bovidaeta import DairyData, EventType

    # On a farm: one farm's SQLite database.
    data = DairyData.from_sqlite("dairy_farm.db")

    # In Databricks: every farm, in Unity Catalog.
    data = DairyData.from_delta("cornell_catalog.cornell_schema")

    # Identical from here on.
    df = data.load_events(subset_events=[EventType.MILK_RECORDING])
    ```

    The arguments are the same either way. **The return type is not**:
    the SQLite path gives you a polars `DataFrame`, the Delta path a Spark
    `DataFrame`, because that is what each environment wants to work in.
    So `df.height` becomes `df.count()`, and an analysis script does not
    move from one backend to the other untouched - swapping the
    constructor is the start of the port, not the whole of it. Use
    `bovidaeta.to_polars` to bring a Delta result into polars once it is
    small enough to fit on the driver.

    Construct with `from_sqlite` or `from_delta` rather than calling
    `DairyData(...)` directly.
    """

    def __init__(self, backend: EventBackend):
        self._backend = backend

    @classmethod
    def from_sqlite(cls, db_path: str | Path = "/data/dairy_farm.db") -> "DairyData":
        """Read one farm's local SQLite database.

        Args:
            db_path: Path to the farm's `.db` file, in the format described
                by `bovidaeta/schemas/sqlite.sql`.
        """
        from .sqlite import _SQLiteBackend

        return cls(_SQLiteBackend(db_path))

    @classmethod
    def from_delta(
        cls,
        catalog_schema: str = "cornell_catalog.cornell_schema",
        spark: "SparkSession | None" = None,
    ) -> "DairyData":
        """Read the multi-farm Delta tables in Unity Catalog.

        Needs Spark: already present inside a Databricks notebook,
        otherwise `pip install 'bovidaeta[delta]'`.

        Args:
            catalog_schema: Fully qualified `catalog.schema` holding the
                `herds`, `cows` and `events` tables.
            spark: Session to use. Defaults to the active one, which is
                what you want in a notebook.
        """
        from .delta import _DeltaBackend

        return cls(_DeltaBackend(catalog_schema, spark))

    @property
    def backend(self) -> str:
        """Which store this instance reads: `"sqlite"` or `"delta"`."""
        return self._backend.name

    def __repr__(self) -> str:
        return f"DairyData({self._backend!r})"

    def load_events(
        self,
        dts_start: datetime | None = None,
        dts_end: datetime | None = None,
        subset_events: Iterable[EventType | str] | None = None,
        subset_metadata: Iterable[str] | Mapping[str, str] | None = None,
        subset_cows: Iterable[str] | None = None,
        subset_herds: Iterable[str] | None = None,
    ) -> Any:
        """Load events, filtered.

        All six filters are optional and combine with AND. Using them is
        strongly preferred over loading everything and filtering in
        memory: they decide what gets read, not what is kept. On a farm
        device that is the difference between fitting in memory and not.
        On Delta it is larger still - the table holds every farm, and
        `subset_events` together with a datetime range lets the engine
        skip whole partitions, since `events` is partitioned by
        `(event_type, event_year)`.

        Args:
            dts_start: Inclusive lower bound on `datetime`.
            dts_end: Inclusive upper bound on `datetime`.
            subset_events: Only these event types.
            subset_metadata: Top-level metadata keys to pull out as
                columns, instead of returning the raw `metadata` blob.
                Either an iterable of keys, or a `{key: "DOUBLE"}` mapping
                to cast them. On Delta the cast matters: metadata is
                stored as VARIANT, which will not aggregate uncast.
            subset_cows: Only these `animal_id`s.
            subset_herds: Only cows in these `herd_id`s, resolved through
                the cows table.

        Returns:
            One row per event, with columns `event_id`, `animal_id`,
            `event_type`, `datetime`, then either `metadata` or one column
            per requested key. A polars `DataFrame` from SQLite, a Spark
            `DataFrame` from Delta.
        """
        dts_start, dts_end = validate_datetime_range(dts_start, dts_end)
        return self._backend.load_events(
            dts_start=dts_start,
            dts_end=dts_end,
            event_types=normalise_event_types(subset_events),
            metadata=normalise_metadata(subset_metadata),
            cow_ids=normalise_ids(subset_cows),
            herd_ids=normalise_ids(subset_herds),
        )

    def load_cows(
        self,
        subset_cows: Iterable[str] | None = None,
        subset_herds: Iterable[str] | None = None,
    ) -> Any:
        """Load cows.

        The two backends differ in shape here: SQLite keeps cow attributes
        in a JSON `metadata` column, while the Delta `cows` table has them
        as typed columns. Delta's is also a bridge table - a cow that
        moves between farms keeps its `animal_id` and gains a row per
        herd - so it can hold more than one row per animal.
        """
        return self._backend.load_cows(
            cow_ids=normalise_ids(subset_cows),
            herd_ids=normalise_ids(subset_herds),
        )

    def load_herds(self, subset_herds: Iterable[str] | None = None) -> Any:
        """Load herds. A farm database holds one; the Delta table holds all."""
        return self._backend.load_herds(herd_ids=normalise_ids(subset_herds))
