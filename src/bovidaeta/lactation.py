"""Lactations and days in milk, derived from the event store.

Neither is stored. A farm's events record calvings and milkings; a lactation
is the span from a calving to whatever ends it (the next calving, a dry-off,
or the cow leaving), and days in milk is a record's distance from its
calving. `load_lactations` derives the spans, `load_lactation_records`
attaches daily yields to them, and `load_daily_milk_yields` gives one milk
yield per cow per day from the milk meter data.

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
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import narwhals.stable.v2 as nw
import polars as pl

from .enums import AggregationPeriod, EventType

if TYPE_CHECKING:  # pragma: no cover
    from narwhals.typing import IntoFrameT

#: Events that close a lactation without a new calving.
CLOSING_EVENTS: tuple[EventType, ...] = (EventType.DRY_OFF, EventType.EXIT)

#: Event types carrying a daily milk yield in `metadata.milking_yield`.
#: `MILK_METER_YIELDS` is per milking session and summed per milking day;
#: `AGGREGATED_MILK_METER_YIELDS` counts only when aggregated per single day.
YIELD_EVENTS: tuple[EventType, ...] = (
    EventType.MILK_RECORDING,
    EventType.MILK_METER_YIELDS,
    EventType.AGGREGATED_MILK_METER_YIELDS,
)

#: On a day with both, the milkings count as measured when they add up to
#: the day's total within this share. A source can miss milkings; its daily
#: total then still reports the whole day, and the milkings fall short of it.
MEASURED_TOLERANCE = 0.02

#: `source` values: which data a daily yield came from.
SOURCE_MILK_RECORDING = "milk_recording"
SOURCE_MILKINGS = "milkings"
SOURCE_DAILY_TOTAL = "daily_total"

DAILY_YIELD_SCHEMA: dict[str, pl.DataType] = {
    "animal_id": pl.String,
    "date": pl.Date,
    "milking_yield": pl.Float64,
    "source": pl.String,
}

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
    "source": pl.String,
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


def _milk_day(frame: nw.LazyFrame) -> nw.Expr:
    """A milking's day: its `milk_date` when the source sent one.

    Without it, the date of its `datetime`, which puts a night milking that
    runs past midnight on the next day.
    """
    milk_date = nw.col("milk_date").cast(nw.String).str.to_date("%Y-%m-%d")
    return nw.coalesce(milk_date, _to_date(frame)).alias("date")


def _day_number(column: str) -> nw.Expr:
    """Days since 0001-01-01, so that subtracting two gives days between them.

    Built from year and day-of-year because narwhals cannot subtract dates
    on Spark. The leap days before year `y` are `y//4 - y//100 + y//400`.
    """
    year = nw.col(column).dt.year().cast(nw.Int64) - 1
    return (
        365 * year
        + year // 4
        - year // 100
        + year // 400
        + nw.col(column).dt.ordinal_day()
    )


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
            lactation_number=is_calving.cast(nw.Int32)
            .cum_sum()
            .over("animal_id", order_by=order),
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
        condition = nw.col("lactation_number") == nw.col("lactation_number").max().over(
            "animal_id"
        )
    elif isinstance(lactation, int):
        condition = nw.col("lactation_number") == lactation
    else:
        condition = nw.col("calving_date") == nw.lit(lactation, dtype=nw.Date)
    return frame.filter(condition).to_native()


def _bounds(
    dts_start: date | None, dts_end: date | None
) -> tuple[datetime | None, datetime | None]:
    """Datetime bounds for reading the days `dts_start`..`dts_end`.

    A day longer on each side: a milking's day can differ from the date of
    its `datetime`, and a day read only in part would look short.
    """
    lo = (
        datetime.combine(dts_start - timedelta(days=1), time.min) if dts_start else None
    )
    hi = datetime.combine(dts_end + timedelta(days=1), time.max) if dts_end else None
    return lo, hi


def _in_days(
    frame: nw.LazyFrame, dts_start: date | None, dts_end: date | None
) -> nw.LazyFrame:
    if dts_start:
        frame = frame.filter(nw.col("date") >= nw.lit(dts_start, dtype=nw.Date))
    if dts_end:
        frame = frame.filter(nw.col("date") <= nw.lit(dts_end, dtype=nw.Date))
    return frame


def _as_date(value: date | datetime | str | None) -> date | None:
    if isinstance(value, str):
        value = date.fromisoformat(value[:10])
    if isinstance(value, datetime):
        value = value.date()
    return value


def _yields(
    data,
    event_type: EventType,
    subset_cows: Iterable[str] | None,
    subset_herds: Iterable[str] | None,
    dts_start: date | None,
    dts_end: date | None,
) -> tuple[nw.LazyFrame, bool]:
    """One yield per cow per day from one event type: `animal_id`, `date`, `milking_yield`.

    Milkings are summed per milking day, and only daily aggregates are used.
    """
    subset_metadata = {"milking_yield": "DOUBLE"}
    if event_type == EventType.MILK_METER_YIELDS:
        subset_metadata |= {"milk_date": "STRING"}
    if event_type == EventType.AGGREGATED_MILK_METER_YIELDS:
        subset_metadata |= {"aggregation_period": "STRING", "aggregation_length": "INT"}
    lo, hi = _bounds(dts_start, dts_end)
    events, eager = _lazy(
        data.load_events(
            dts_start=lo,
            dts_end=hi,
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
            (
                nw.col("aggregation_period").cast(nw.String)
                == AggregationPeriod.DAY.value
            )
            & (nw.col("aggregation_length").cast(nw.Int64).fill_null(1) == 1)
        )
    day = (
        _milk_day(events)
        if event_type == EventType.MILK_METER_YIELDS
        else _to_date(events)
    )
    records = events.select(
        "animal_id", day, nw.col("milking_yield").cast(nw.Float64)
    ).drop_nulls("milking_yield")
    if event_type == EventType.MILK_METER_YIELDS:
        records = records.group_by("animal_id", "date").agg(
            nw.col("milking_yield").sum()
        )
    return _in_days(records, dts_start, dts_end), eager


def _daily_milk_yields(
    data,
    subset_cows: Iterable[str] | None,
    subset_herds: Iterable[str] | None,
    dts_start: date | None,
    dts_end: date | None,
    prefer: str,
) -> tuple[nw.LazyFrame, bool]:
    if prefer not in (SOURCE_DAILY_TOTAL, SOURCE_MILKINGS):
        raise ValueError(
            f"prefer must be {SOURCE_DAILY_TOTAL!r} or {SOURCE_MILKINGS!r}, got {prefer!r}"
        )

    scope = (subset_cows, subset_herds, dts_start, dts_end)
    milkings, eager = _yields(data, EventType.MILK_METER_YIELDS, *scope)
    totals, _ = _yields(data, EventType.AGGREGATED_MILK_METER_YIELDS, *scope)

    # One row per cow-day holding both figures, either of which can be
    # missing: a concat and group_by, which every engine runs lazily.
    none = nw.lit(None, dtype=nw.Float64)
    days = (
        nw.concat(
            [
                milkings.select(
                    "animal_id", "date", milkings=nw.col("milking_yield"), total=none
                ),
                totals.select(
                    "animal_id", "date", milkings=none, total=nw.col("milking_yield")
                ),
            ],
            how="vertical",
        )
        .group_by("animal_id", "date")
        .agg(nw.col("milkings").max(), nw.col("total").max())
    )

    has_milkings = ~nw.col("milkings").is_null()
    has_total = ~nw.col("total").is_null()
    # For a cow with daily totals, a day without one is not finished (today)
    # or not reported, and its milkings can't be checked: it is left out.
    # Only for a cow without any do the milkings stand on their own.
    no_totals = nw.col("total").count().over("animal_id") == 0
    days = days.filter(has_total | no_totals)
    if prefer == SOURCE_DAILY_TOTAL:
        use_total = has_total
    else:
        complete = (
            nw.col("milkings") - nw.col("total")
        ).abs() <= MEASURED_TOLERANCE * nw.col("total")
        days = days.filter(~has_milkings | ~has_total | complete)
        use_total = ~has_milkings
    out = days.select(
        "animal_id",
        "date",
        nw.when(use_total)
        .then(nw.col("total"))
        .otherwise(nw.col("milkings"))
        .alias("milking_yield"),
        nw.when(use_total)
        .then(nw.lit(SOURCE_DAILY_TOTAL))
        .otherwise(nw.lit(SOURCE_MILKINGS))
        .alias("source"),
    )
    return out, eager


def load_daily_milk_yields(
    data,
    subset_cows: Iterable[str] | None = None,
    subset_herds: Iterable[str] | None = None,
    dts_start: date | datetime | str | None = None,
    dts_end: date | datetime | str | None = None,
    prefer: str = SOURCE_DAILY_TOTAL,
) -> Any:
    """One milk yield per cow per day, from the milk meter data.

    A farm can have two kinds: the individual milkings (`MILK_METER_YIELDS`,
    summed per milking day) and daily totals (`AGGREGATED_MILK_METER_YIELDS`).
    They are never added together; each cow-day gets one figure.

    A source can miss milkings while its daily total still reports the whole
    day (filled in by the source system), so on such a day the two disagree.

    Args:
        data: A `DairyData` source.
        subset_cows: Only these `animal_id`s.
        subset_herds: Only cows in these `herd_id`s.
        dts_start, dts_end: Only these days (inclusive).
        prefer: `"daily_total"` (default): the daily total - for totals
            and averages, which should count the whole day. `"milkings"`:
            the summed milkings, on days where they add up to the daily
            total; days without milkings get the daily total - for measured
            values, such as fitting a curve. Either way, a cow without any
            daily totals gets her summed milkings, and for a cow with daily
            totals a day without one (such as today) is left out.

    Returns:
        Columns `animal_id`, `date`, `milking_yield`, `source`
        (`"milkings"` or `"daily_total"`). A polars `DataFrame` from SQLite,
        a Spark `DataFrame` from Delta.
    """
    out, eager = _daily_milk_yields(
        data, subset_cows, subset_herds, _as_date(dts_start), _as_date(dts_end), prefer
    )
    return _native(out.select(*DAILY_YIELD_SCHEMA).sort("animal_id", "date"), eager)


def load_lactation_records(
    data,
    lactations: Any = None,
    subset_cows: Iterable[str] | None = None,
    subset_herds: Iterable[str] | None = None,
    event_type: EventType | None = EventType.MILK_RECORDING,
    min_dim: int = 1,
    max_dim: int | None = None,
    prefer: str = SOURCE_MILKINGS,
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
            `MILK_METER_YIELDS` (one per milking session, summed per milking
            day), `AGGREGATED_MILK_METER_YIELDS` (only its daily totals are
            used; weekly or monthly ones are dropped), or `None` for both
            kinds of milk meter data combined, as `load_daily_milk_yields`
            with `prefer` does.
        min_dim: Drop records below this days in milk. The default of 1
            drops the calving day itself.
        max_dim: Drop records beyond this days in milk. Worth setting to
            `305` for anything that assumes a standard lactation: a cow that
            is never dried off keeps producing records, and her lactation
            can run for years.
        prefer: With `event_type=None`, see `load_daily_milk_yields`. The
            default `"milkings"` keeps measured days, which is what a
            lactation curve should be fitted on.

    Returns:
        Columns `animal_id`, `lactation_number`, `calving_date`, `date`,
        `dim`, `milking_yield` and `source` (`"milk_recording"`,
        `"milkings"` or `"daily_total"`), sorted by cow, lactation and
        `dim`. A polars `DataFrame` from SQLite, a Spark `DataFrame` from
        Delta.
    """
    if event_type is not None and event_type not in YIELD_EVENTS:
        raise ValueError(
            f"event_type must be None or one of {YIELD_EVENTS}, got {event_type!r}"
        )

    if lactations is None:
        lactations = load_lactations(
            data, subset_cows=subset_cows, subset_herds=subset_herds
        )
    lactations, eager = _lazy(lactations)
    lactations = lactations.select(
        "animal_id", "lactation_number", "calving_date", "end_date"
    )

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
            source=nw.lit(None, dtype=nw.String),
        )
        return _native(empty.select(*RECORD_SCHEMA), eager)

    if event_type is None:
        records, _ = _daily_milk_yields(
            data, subset_cows, subset_herds, first_calving, None, prefer
        )
    else:
        records, _ = _yields(
            data, event_type, subset_cows, subset_herds, first_calving, None
        )
        source = {
            EventType.MILK_RECORDING: SOURCE_MILK_RECORDING,
            EventType.MILK_METER_YIELDS: SOURCE_MILKINGS,
            EventType.AGGREGATED_MILK_METER_YIELDS: SOURCE_DAILY_TOTAL,
        }[EventType(event_type)]
        records = records.with_columns(source=nw.lit(source))

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

    return _native(
        out.select(*RECORD_SCHEMA).sort("animal_id", "lactation_number", "dim"), eager
    )


__all__ = [
    "CLOSING_EVENTS",
    "DAILY_YIELD_SCHEMA",
    "LACTATION_SCHEMA",
    "MEASURED_TOLERANCE",
    "RECORD_SCHEMA",
    "SOURCE_DAILY_TOTAL",
    "SOURCE_MILKINGS",
    "SOURCE_MILK_RECORDING",
    "YIELD_EVENTS",
    "load_daily_milk_yields",
    "load_lactation_records",
    "load_lactations",
    "select_lactations",
]
