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
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime, time

import polars as pl

from .enums import AggregationPeriod, EventType

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


def _dates(events: pl.DataFrame) -> pl.DataFrame:
    """Event rows reduced to (animal_id, event_type, date), deduplicated.

    Two calvings on one day are one calving: twins are recorded as a row per
    calf, and counting them twice would shift every later lactation number.
    """
    if events.is_empty():
        return pl.DataFrame(
            schema={"animal_id": pl.String, "event_type": pl.String, "date": pl.Date}
        )

    return events.select(
        "animal_id",
        "event_type",
        pl.col("datetime").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("date"),
    ).unique()


def load_lactations(
    data,
    subset_cows: Iterable[str] | None = None,
    subset_herds: Iterable[str] | None = None,
) -> pl.DataFrame:
    """One row per lactation, numbered per cow in calving order.

    Args:
        data: A `DairyData` source.
        subset_cows: Only these `animal_id`s.
        subset_herds: Only cows in these `herd_id`s.

    Returns:
        Columns `animal_id`, `lactation_number` (1 for the first calving on
        record), `calving_date`, `end_date`, `end_reason` — one of
        `"Calving"`, `"DryOff"`, `"Exit"`, or `"open"` for the lactation the
        cow is still in, whose `end_date` is null.

        A lactation that began before the data starts is not represented:
        without its calving there is nothing to measure days in milk from.
    """
    events = _dates(
        data.load_events(
            subset_events=[EventType.CALVING, *CLOSING_EVENTS],
            subset_cows=subset_cows,
            subset_herds=subset_herds,
        )
    )

    calvings = (
        events.filter(pl.col("event_type") == EventType.CALVING.value)
        .select("animal_id", "date")
        .sort("animal_id", "date")
        .with_columns(
            lactation_number=pl.col("date").rank("ordinal").over("animal_id").cast(pl.Int32),
            next_calving=pl.col("date").shift(-1).over("animal_id"),
        )
    )
    if calvings.is_empty():
        return pl.DataFrame(schema=LACTATION_SCHEMA)

    closers = (
        events.filter(pl.col("event_type").is_in([e.value for e in CLOSING_EVENTS]))
        .select(
            "animal_id",
            pl.col("date").alias("close_date"),
            pl.col("event_type").alias("close_reason"),
        )
        .sort("close_date")
    )

    # The first dry-off or exit at or after the calving ends the lactation,
    # unless the cow calves again first. A dry-off *before* a calving belongs
    # to the previous lactation and is skipped by the forward search.
    return (
        calvings.sort("date")
        .join_asof(
            closers,
            left_on="date",
            right_on="close_date",
            by="animal_id",
            strategy="forward",
            # Both frames are sorted directly above. Polars cannot verify that
            # per group and warns on every call; the warning is captured as
            # tool output and charged to the agent's context, so say so here.
            check_sortedness=False,
        )
        .with_columns(end_date=pl.min_horizontal("next_calving", "close_date"))
        .with_columns(
            end_reason=pl.when(pl.col("end_date").is_null())
            .then(pl.lit("open"))
            .when(pl.col("end_date") == pl.col("next_calving"))
            .then(pl.lit(EventType.CALVING.value))
            .otherwise(pl.col("close_reason"))
        )
        .select(
            "animal_id",
            "lactation_number",
            pl.col("date").alias("calving_date"),
            "end_date",
            "end_reason",
        )
        .sort("animal_id", "lactation_number")
    )


def select_lactations(
    lactations: pl.DataFrame, lactation: str | int | date = "latest"
) -> pl.DataFrame:
    """Narrow a `load_lactations` frame to one lactation per cow.

    Args:
        lactations: The frame to filter.
        lactation: `"latest"` for each cow's most recent calving, an `int`
            for that `lactation_number`, or a date (or ISO string) for the
            lactation that started on it.
    """
    if isinstance(lactation, str) and lactation != "latest":
        lactation = date.fromisoformat(lactation)

    if lactation == "latest":
        return lactations.filter(
            pl.col("lactation_number") == pl.col("lactation_number").max().over("animal_id")
        )
    if isinstance(lactation, int):
        return lactations.filter(pl.col("lactation_number") == lactation)
    return lactations.filter(pl.col("calving_date") == lactation)


def load_lactation_records(
    data,
    lactations: pl.DataFrame | None = None,
    subset_cows: Iterable[str] | None = None,
    subset_herds: Iterable[str] | None = None,
    event_type: EventType = EventType.MILK_RECORDING,
    min_dim: int = 1,
    max_dim: int | None = None,
) -> pl.DataFrame:
    """Daily milk yields with a days-in-milk column, per lactation.

    Args:
        data: A `DairyData` source.
        lactations: Lactations to attach records to, from `load_lactations`
            or `select_lactations`. Defaults to every lactation of the cows
            in scope. Records outside these lactations are dropped, so
            filtering here is also what keeps the query small: only events
            from the earliest `calving_date` onwards are read.
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
        `dim`, `milking_yield`, sorted by cow, lactation and `dim`.
    """
    if event_type not in YIELD_EVENTS:
        raise ValueError(f"event_type must be one of {YIELD_EVENTS}, got {event_type!r}")

    if lactations is None:
        lactations = load_lactations(data, subset_cows=subset_cows, subset_herds=subset_herds)
    if lactations.is_empty():
        return pl.DataFrame(schema=RECORD_SCHEMA)

    subset_metadata = {"milking_yield": "DOUBLE"}
    if event_type == EventType.AGGREGATED_MILK_METER_YIELDS:
        subset_metadata |= {"aggregation_period": "STRING", "aggregation_length": "INT"}
    events = data.load_events(
        dts_start=datetime.combine(lactations["calving_date"].min(), time.min),
        subset_events=[event_type],
        subset_metadata=subset_metadata,
        subset_cows=subset_cows,
        subset_herds=subset_herds,
    )
    if events.is_empty():
        return pl.DataFrame(schema=RECORD_SCHEMA)

    if event_type == EventType.AGGREGATED_MILK_METER_YIELDS:
        # aggregation_length defaults to 1 in the model, so a missing one is daily.
        events = events.filter(
            (pl.col("aggregation_period") == AggregationPeriod.DAY.value)
            & (pl.col("aggregation_length").fill_null(1) == 1)
        )
    records = events.select(
        "animal_id",
        pl.col("datetime").str.slice(0, 10).str.to_date("%Y-%m-%d").alias("date"),
        pl.col("milking_yield").cast(pl.Float64),
    ).drop_nulls("milking_yield")
    if event_type == EventType.MILK_METER_YIELDS:
        records = records.group_by("animal_id", "date").agg(pl.col("milking_yield").sum())

    out = (
        records.sort("date")
        .join_asof(
            lactations.sort("calving_date").select(
                "animal_id", "lactation_number", "calving_date", "end_date"
            ),
            left_on="date",
            right_on="calving_date",
            by="animal_id",
            strategy="backward",
            check_sortedness=False,
        )
        .drop_nulls("lactation_number")
        .filter(pl.col("end_date").is_null() | (pl.col("date") < pl.col("end_date")))
        .with_columns(
            dim=(pl.col("date") - pl.col("calving_date")).dt.total_days().cast(pl.Int32)
        )
        .filter(pl.col("dim") >= min_dim)
    )
    if max_dim is not None:
        out = out.filter(pl.col("dim") <= max_dim)

    return out.select(*RECORD_SCHEMA).sort("animal_id", "lactation_number", "dim")


__all__ = [
    "CLOSING_EVENTS",
    "LACTATION_SCHEMA",
    "RECORD_SCHEMA",
    "YIELD_EVENTS",
    "load_lactation_records",
    "load_lactations",
    "select_lactations",
]
