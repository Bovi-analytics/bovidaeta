"""`DairyData` - the single loader for dairy farm event data."""

from collections.abc import Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..enums import EventType
from .base import (
    EventBackend,
    normalise_event_types,
    normalise_farm_numbers,
    normalise_ids,
    normalise_metadata,
    validate_datetime_range,
)

if TYPE_CHECKING:  # pragma: no cover
    from pyspark.sql import SparkSession


class DairyData:
    """Load events, cows, herds and studies, from whichever store they live in.

    The same data is kept two ways, and one class reads both:

    ```python
    from bovidaeta import DairyData, EventType

    # On a farm: one farm's SQLite database.
    data = DairyData.from_sqlite("dairy_farm.db")

    # In Databricks: every farm, in Unity Catalog.
    data = DairyData.from_delta("bovidaeta.farms")

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
    def from_sqlite(
        cls, db_path: str | Path = "/data/dairy_farm.db", immutable: bool = False
    ) -> "DairyData":
        """Read one farm's local SQLite database.

        The file is always opened read-only.

        Args:
            db_path: Path to the farm's `.db` file, in the format described
                by `bovidaeta/schemas/sqlite.sql`.
            immutable: Promise SQLite the file will never change, letting it
                skip the WAL and all locking. Only for a frozen snapshot or a
                file on read-only media. Leave it off for a live database:
                against a file something else writes to, an immutable read has
                no lock and can return half-written pages without an error.
        """
        from .sqlite import _SQLiteBackend

        return cls(_SQLiteBackend(db_path, immutable=immutable))

    @classmethod
    def from_delta(
        cls,
        catalog_schema: str,
        spark: "SparkSession | None" = None,
    ) -> "DairyData":
        """Read the multi-farm Delta tables in Unity Catalog.

        Needs Spark: already present inside a Databricks notebook,
        otherwise `pip install 'bovidaeta[delta]'`.

        Args:
            catalog_schema: Fully qualified `catalog.schema` holding the
                `herds`, `cows` and `animal_events` tables, e.g. `"bovidaeta.farms"`.
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
        subset_studies: Iterable[str] | None = None,
    ) -> Any:
        """Load events, filtered.

        All seven filters are optional and combine with AND. Using them is
        strongly preferred over loading everything and filtering in
        memory: they decide what gets read, not what is kept. On a farm
        device that is the difference between fitting in memory and not.
        On Delta it is larger still - the table holds every farm, and
        `subset_events` together with a datetime range lets the engine
        skip whole partitions, since `animal_events` is partitioned by
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
            subset_studies: Only events recorded by these `study_id`s.
                This leaves out farm data (whose `study_id` is null) and
                anything the same animals had recorded in other studies; for
                an animal's full history, pass the animals of a study (see
                `load_study_animals`) as `subset_cows` instead.

        Returns:
            One row per event, with columns `event_id`, `animal_id`,
            `event_type`, `datetime`, `study_id` (null for farm data), then
            either `metadata` or one column per requested key. A polars `DataFrame` from SQLite, a Spark
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
            study_ids=normalise_ids(subset_studies),
        )

    def load_cows(
        self,
        subset_cows: Iterable[str] | None = None,
        subset_herds: Iterable[str] | None = None,
        subset_farm_numbers: Iterable[int | str] | None = None,
    ) -> Any:
        """Load cows.

        The two backends differ in shape here: SQLite keeps cow attributes
        in a JSON `metadata` column, while the Delta `cows` table has them
        as typed columns. Delta's is also a bridge table - a cow that
        moves between farms keeps its `animal_id` and gains a row per
        herd - so it can hold more than one row per animal.

        Args:
            subset_cows: Only these `animal_id`s.
            subset_herds: Only cows in these `herd_id`s.
            subset_farm_numbers: Only cows with these `animal_farm_number`s
                (ints, or numeric strings). `animal_id` is a UUID, so this is
                how a caller looks up the cow a person named: the farm
                (work) number is what is on the cow's collar and what a
                farmer types. A farm can reuse a number over time, so one
                number can match more than one cow; prefer the one without
                an `exit_date`.
        """
        return self._backend.load_cows(
            cow_ids=normalise_ids(subset_cows),
            herd_ids=normalise_ids(subset_herds),
            farm_numbers=normalise_farm_numbers(subset_farm_numbers),
        )

    def load_herds(self, subset_herds: Iterable[str] | None = None) -> Any:
        """Load herds. A farm database holds one; the Delta table holds all."""
        return self._backend.load_herds(herd_ids=normalise_ids(subset_herds))

    def load_studies(self, subset_studies: Iterable[str] | None = None) -> Any:
        """Load research studies. Empty for farm data.

        Columns as in `bovidaeta.Study`: `study_id`, `project`, `name`,
        `description`, `start_date`, `end_date`, `doi_or_protocol_url`,
        `open_data`, `license`, `credit_required`, `contributors`. Dates are
        ISO-8601 strings from SQLite and `DATE`s from Delta.

        Args:
            subset_studies: Only these `study_id`s.
        """
        return self._backend.load_studies(study_ids=normalise_ids(subset_studies))

    def load_study_animals(self, subset_studies: Iterable[str] | None = None) -> Any:
        """Load which animals took part in which study.

        Columns `study_id`, `animal_id`, `study_group` (e.g. the treatment
        arm). An animal in several studies has a row per study. To get the
        full history of a study's animals, pass their ids on:

        ```python
        animals = data.load_study_animals(subset_studies=[study_id])
        events = data.load_events(subset_cows=animals["animal_id"])  # polars
        ```

        Args:
            subset_studies: Only these `study_id`s.
        """
        return self._backend.load_study_animals(study_ids=normalise_ids(subset_studies))
