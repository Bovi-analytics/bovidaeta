"""Lactations and days in milk, derived from the event store.

Neither is stored. A farm's events record calvings and milkings; a lactation
is the span from a calving to whatever ends it (the next calving, a dry-off,
or the cow leaving), and days in milk is a record's distance from its
calving. `load_lactations` derives the spans, `load_lactation_records`
attaches daily yields to them.

```python
from bovidaeta import DairyData
from bovidaeta.lactation import load_lactations, load_lactation_records, select_lactations

data = DairyData.from_sqlite("dairy_farm.db")
current = select_lactations(load_lactations(data, subset_cows=[animal_id]), "latest")
records = load_lactation_records(data, lactations=current, subset_cows=[animal_id], max_dim=305)
```

Pass `subset_cows` to both calls when you want one cow: it is the difference
between an indexed lookup and a scan of every milking on the farm.

Both backends are supported, and each gets its own frame back, as with
`DairyData.load_events`: a polars `DataFrame` from SQLite, a lazy Spark
`DataFrame` from Delta. The logic is written once against narwhals, which
translates it to whichever engine the data lives in, so on Delta nothing is
collected to the driver until you ask for it.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any

import narwhals.stable.v2 as nw
import polars as pl

from .enums import AggregationPeriod, EventType

if TYPE_CHECKING:  # pragma: no cover
    from narwhals.typing import IntoFrameT

#: Events that close a lactation without a new calving.
CLOSING_EVENTS: tuple[EventType, ...] = (EventType.DRY_OFF, EventType.EXIT)

#: Event types carrying a daily milk yield in `metadata.milking_yield`.
#: `MILK_METER_YIELDS` is per milking session and summed per day;
#: `AGGREGATED_MILK_METER_YIELDS` counts only when aggregated per single day.
YIELD_EVENTS: tuple[EventType, ...] = (
    EventType.MILK_RECORDING,
    EventType.MILK_METER_YIELDS,
    EventType.AGGREGATED_MILK_METER_YIELDS,
)

LACTATION_SCHEMA: dict[str, pl.DataType] = {
    "animal_id": pl.String,
    "lactation_number": pl.Int32,
    "calving_date": pl.Date,
    "end_date": pl.Date,
    "end_reason": pl.String,
}

RECORD_SCHEMA: dict[str, pl.DataType] = {
    "animal_id": pl.String,
    "lactation_number": pl.Int32,
    "calving_date": pl.Date,
    "date": pl.Date,
    "dim": pl.Int32,
    "milking_yield": pl.Float64,
}


def _lazy(native: Any) -> tuple[nw.LazyFrame, bool]:
    """Wrap a backend frame as a narwhals `LazyFrame`, noting if it was eager.

    Everything below runs lazily either way. An eager input (polars, from
    SQLite) is collected again on the way out by `_native`, so callers get
    back the kind of frame they put in.
    """
    frame = nw.from_native(native)
    if isinstance(frame, nw.DataFrame):
        return frame.lazy(), True
    return frame, False


def _native(frame: nw.LazyFrame, eager: bool) -> Any:
    return frame.collect().to_native() if eager else frame.to_native()


def _to_date(frame: nw.LazyFrame) -> nw.Expr:
    """`datetime` as a date. SQLite stores it as ISO text, Delta as TIMESTAMP."""
    col = nw.col("datetime")
    if frame.collect_schema()["datetime"] == nw.String:
        return col.str.slice(0, 10).str.to_date("%Y-%m-%d").alias("date")
    return col.dt.date().alias("date")


def _day_number(column: str) -> nw.Expr:
    """Days since 0001-01-01, so that subtracting two gives days between them.

    Built from year and day-of-year because narwhals cannot subtract dates
    on Spark. The leap days before year `y` are `y//4 - y//100 + y//400`.
    """
    year = nw.col(column).dt.year().cast(nw.Int64) - 1
    return 365 * year + year // 4 - year // 100 + year // 400 + nw.col(column).dt.ordinal_day()


def load_lactations(
    data,
    subset_cows: Iterable[str] | None = None,
    subset_herds: Iterable[str] | None = None,
) -> Any:
    """One row per lactation, numbered per cow in calving order.

    Args:
        data: A `DairyData` source.
        subset_cows: Only these `animal_id`s.
        subset_herds: Only cows in these `herd_id`s.

    Returns:
        Columns `animal_id`, `lactation_number` (1 for the first calving on
        record), `calving_date`, `end_date`, `end_reason` — one of
        `"Calving"`, `"DryOff"`, `"Exit"`, or `"open"` for the lactation the
        cow is still in, whose `end_date` is null. A polars `DataFrame` from
        SQLite, a Spark `DataFrame` from Delta.

        A lactation that began before the data starts is not represented:
        without its calving there is nothing to measure days in milk from.
    """
    events, eager = _lazy(
        data.load_events(
            subset_events=[EventType.CALVING, *CLOSING_EVENTS],
            subset_cows=subset_cows,
            subset_herds=subset_herds,
        )
    )

    # Two calvings on one day are one calving: twins are recorded as a row
    # per calf, and counting them twice would shift every later lactation
    # number.
    events = events.select("animal_id", "event_type", _to_date(events)).unique()

    # Lay each cow's calvings and closers out in date order. A lactation ends
    # at whatever follows its calving: the next calving, or a dry-off or exit
    # first. A calving sorts before a closer on the same day, so an exit on
    # the day of calving still closes that lactation, and a dry-off *before*
    # a calving falls to the previous lactation. The event type is only a
    # tie-break, so the result does not depend on the engine's sort.
    is_calving = nw.col("event_type") == EventType.CALVING.value
    order = ["date", "_closer", "event_type"]
    lactations = (
        events.with_columns(_closer=(~is_calving).cast(nw.Int8))
        .with_columns(
            lactation_number=is_calving.cast(nw.Int32).cum_sum().over("animal_id", order_by=order),
            end_date=nw.col("date").shift(-1).over("animal_id", order_by=order),
            next_event=nw.col("event_type").shift(-1).over("animal_id", order_by=order),
        )
        .filter(is_calving)
        .select(
            "animal_id",
            nw.col("lactation_number").cast(nw.Int32),
            nw.col("date").alias("calving_date"),
            nw.col("end_date").cast(nw.Date),
            nw.when(nw.col("end_date").is_null())
            .then(nw.lit("open"))
            .otherwise(nw.col("next_event"))
            .alias("end_reason"),
        )
        .sort("animal_id", "lactation_number")
    )
    return _native(lactations, eager)


def select_lactations(
    lactations: IntoFrameT, lactation: str | int | date = "latest"
) -> IntoFrameT:
    """Narrow a `load_lactations` frame to one lactation per cow.

    Args:
        lactations: The frame to filter, from either backend.
        lactation: `"latest"` for each cow's most recent calving, an `int`
            for that `lactation_number`, or a date (or ISO string) for the
            lactation that started on it.
    """
    if isinstance(lactation, str) and lactation != "latest":
        lactation = date.fromisoformat(lactation)

    frame = nw.from_native(lactations)
    if lactation == "latest":
        condition = nw.col("lactation_number") == nw.col("lactation_number").max().over("animal_id")
    elif isinstance(lactation, int):
        condition = nw.col("lactation_number") == lactation
    else:
        condition = nw.col("calving_date") == nw.lit(lactation, dtype=nw.Date)
    return frame.filter(condition).to_native()


def load_lactation_records(
    data,
    lactations: Any = None,
    subset_cows: Iterable[str] | None = None,
    subset_herds: Iterable[str] | None = None,
    event_type: EventType = EventType.MILK_RECORDING,
    min_dim: int = 1,
    max_dim: int | None = None,
) -> Any:
    """Daily milk yields with a days-in-milk column, per lactation.

    Args:
        data: A `DairyData` source.
        lactations: Lactations to attach records to, from `load_lactations`
            or `select_lactations` on the same `data`. Defaults to every
            lactation of the cows in scope. Records outside these
            lactations are dropped, so filtering here is also what keeps
            the query small: only events from the earliest `calving_date`
            onwards are read.
        subset_cows: Only these `animal_id`s.
        subset_herds: Only cows in these `herd_id`s.
        event_type: `MILK_RECORDING` (one yield per day),
            `MILK_METER_YIELDS` (one per milking session, summed per day) or
            `AGGREGATED_MILK_METER_YIELDS` (only its daily totals are used;
            weekly or monthly ones are dropped).
        min_dim: Drop records below this days in milk. The default of 1
            drops the calving day itself.
        max_dim: Drop records beyond this days in milk. Worth setting to
            `305` for anything that assumes a standard lactation: a cow that
            is never dried off keeps producing records, and her lactation
            can run for years.

    Returns:
        Columns `animal_id`, `lactation_number`, `calving_date`, `date`,
        `dim`, `milking_yield`, sorted by cow, lactation and `dim`. A polars
        `DataFrame` from SQLite, a Spark `DataFrame` from Delta.
    """
    if event_type not in YIELD_EVENTS:
        raise ValueError(f"event_type must be one of {YIELD_EVENTS}, got {event_type!r}")

    if lactations is None:
        lactations = load_lactations(data, subset_cows=subset_cows, subset_herds=subset_herds)
    lactations, eager = _lazy(lactations)
    lactations = lactations.select("animal_id", "lactation_number", "calving_date", "end_date")

    # One small query, worth it: it bounds the events read below, which on
    # Delta lets whole years of partitions be skipped.
    first_calving = lactations.select(nw.col("calving_date").min()).collect().item()
    if first_calving is None:
        # No lactations, so no records. Built from the (empty) `lactations`
        # rather than from scratch, so it is still the backend's own frame.
        empty = lactations.with_columns(
            date=nw.col("calving_date"),
            dim=nw.lit(0, dtype=nw.Int32),
            milking_yield=nw.lit(None, dtype=nw.Float64),
        )
        return _native(empty.select(*RECORD_SCHEMA), eager)

    subset_metadata = {"milking_yield": "DOUBLE"}
    if event_type == EventType.AGGREGATED_MILK_METER_YIELDS:
        subset_metadata |= {"aggregation_period": "STRING", "aggregation_length": "INT"}
    events, _ = _lazy(
        data.load_events(
            dts_start=datetime.combine(first_calving, time.min),
            subset_events=[event_type],
            subset_metadata=subset_metadata,
            subset_cows=subset_cows,
            subset_herds=subset_herds,
        )
    )

    if event_type == EventType.AGGREGATED_MILK_METER_YIELDS:
        # aggregation_length defaults to 1 in the model, so a missing one is
        # daily. Cast because an empty SQLite result types every column as text.
        events = events.filter(
            (nw.col("aggregation_period").cast(nw.String) == AggregationPeriod.DAY.value)
            & (nw.col("aggregation_length").cast(nw.Int64).fill_null(1) == 1)
        )
    records = events.select(
        "animal_id",
        _to_date(events),
        nw.col("milking_yield").cast(nw.Float64),
    ).drop_nulls("milking_yield")
    if event_type == EventType.MILK_METER_YIELDS:
        records = records.group_by("animal_id", "date").agg(nw.col("milking_yield").sum())

    # A cow's lactations never overlap, so each record falls in at most one:
    # the one whose [calving_date, end_date) contains it.
    out = (
        records.join(lactations, on="animal_id", how="inner")
        .filter(
            (nw.col("date") >= nw.col("calving_date"))
            & (nw.col("end_date").is_null() | (nw.col("date") < nw.col("end_date")))
        )
        .with_columns(
            dim=(_day_number("date") - _day_number("calving_date")).cast(nw.Int32)
        )
        .filter(nw.col("dim") >= min_dim)
    )
    if max_dim is not None:
        out = out.filter(nw.col("dim") <= max_dim)

    return _native(out.select(*RECORD_SCHEMA).sort("animal_id", "lactation_number", "dim"), eager)


__all__ = [
    "CLOSING_EVENTS",
    "LACTATION_SCHEMA",
    "RECORD_SCHEMA",
    "YIELD_EVENTS",
    "load_lactation_records",
    "load_lactations",
    "select_lactations",
]
