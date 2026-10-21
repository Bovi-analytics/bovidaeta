"""Delta backend: the multi-farm tables in Unity Catalog.

This is the research / cloud path - many farms in one place, queried
through Spark on Databricks. Reached through `DairyData.from_delta(...)`,
not used directly.

The tables are created by `bovidaeta/schemas/delta.sql` and loaded from
per-farm SQLite exports by `pipelines/sqlite_to_delta.py`.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base import BASE_COLUMNS, EventBackend, validate_identifier

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    import polars as pl
    from pyspark.sql import DataFrame, SparkSession

DEFAULT_CATALOG_SCHEMA = "cornell_catalog.cornell_schema"


def _resolve_spark() -> "SparkSession":
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "DairyData.from_delta needs pyspark. Run this in a Databricks "
            "notebook, or install the extra with `pip install 'bovidaeta[delta]'`."
        ) from exc

    active = SparkSession.getActiveSession()
    if active is not None:
        return active
    return SparkSession.builder.getOrCreate()


class _DeltaBackend(EventBackend):
    name = "delta"

    def __init__(
        self,
        catalog_schema: str = DEFAULT_CATALOG_SCHEMA,
        spark: "SparkSession | None" = None,
    ):
        self.catalog_schema = validate_identifier(catalog_schema, "catalog.schema")
        self._spark = spark

    def __repr__(self) -> str:
        return f"delta:{self.catalog_schema}"

    @property
    def spark(self) -> "SparkSession":
        if self._spark is None:
            self._spark = _resolve_spark()
        return self._spark

    def _table(self, name: str) -> str:
        return f"{self.catalog_schema}.{name}"

    @staticmethod
    def _in_clause(
        column: str, values: list[str], prefix: str, args: dict[str, Any]
    ) -> str:
        """`col IN (:p0, :p1, ...)`, registering each value as a scalar param.

        Spark's named-parameter support binds scalars rather than lists, so
        an IN list is expanded into one placeholder per value.
        """
        names = []
        for i, value in enumerate(values):
            name = f"{prefix}_{i}"
            args[name] = value
            names.append(f":{name}")
        return f"{column} IN ({', '.join(names)})"

    @staticmethod
    def _metadata_projection(metadata: dict[str, str | None]) -> list[str]:
        """`metadata:key::TYPE AS key`.

        An uncast VARIANT will not aggregate, so pass `subset_metadata` as
        a `{key: type}` mapping unless you want the raw variant back.
        """
        cols = []
        for key, cast in metadata.items():
            expr = f"metadata:{key}"
            if cast:
                expr = f"{expr}::{cast}"
            cols.append(f"{expr} AS {key}")
        return cols

    def load_events(
        self,
        dts_start: datetime | None,
        dts_end: datetime | None,
        event_types: list[str] | None,
        metadata: dict[str, str | None] | None,
        cow_ids: list[str] | None,
        herd_ids: list[str] | None,
    ) -> "DataFrame":
        select_cols = list(BASE_COLUMNS)
        if metadata:
            select_cols += self._metadata_projection(metadata)
        else:
            select_cols.append("metadata")

        conditions: list[str] = []
        args: dict[str, Any] = {}

        if dts_start:
            conditions.append("datetime >= :dts_start")
            args["dts_start"] = dts_start
            # Redundant with the line above, but stated on the partition
            # column so Delta can prune whole years instead of opening
            # every file to check its datetimes.
            conditions.append("event_year >= :year_start")
            args["year_start"] = dts_start.year
        if dts_end:
            conditions.append("datetime <= :dts_end")
            args["dts_end"] = dts_end
            conditions.append("event_year <= :year_end")
            args["year_end"] = dts_end.year
        if event_types:
            conditions.append(
                self._in_clause("event_type", event_types, "event_type", args)
            )
        if cow_ids:
            conditions.append(self._in_clause("animal_id", cow_ids, "cow", args))
        if herd_ids:
            # Events carry no herd column; membership lives in the cows
            # bridge table, since a cow that moves farms keeps its
            # animal_id and gains a second row there.
            herd_filter = self._in_clause("herd_id", herd_ids, "herd", args)
            conditions.append(
                f"animal_id IN (SELECT animal_id FROM {self._table('cows')} WHERE {herd_filter})"
            )

        query = f"SELECT {', '.join(select_cols)} FROM {self._table('events')}"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        return self.spark.sql(query, args=args)

    def load_cows(
        self,
        cow_ids: list[str] | None,
        herd_ids: list[str] | None,
        sire_ear_tags: list[str] | None,
    ) -> "DataFrame":
        conditions: list[str] = []
        args: dict[str, Any] = {}
        if cow_ids:
            conditions.append(self._in_clause("animal_id", cow_ids, "cow", args))
        if herd_ids:
            conditions.append(self._in_clause("herd_id", herd_ids, "herd", args))
        if sire_ear_tags:
            conditions.append(
                self._in_clause(
                    "upper(sire_ear_tag)",
                    [t.upper() for t in sire_ear_tags],
                    "tag",
                    args,
                )
            )

        query = f"SELECT * FROM {self._table('cows')}"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        return self.spark.sql(query, args=args)

    def load_herds(self, herd_ids: list[str] | None) -> "DataFrame":
        query = f"SELECT * FROM {self._table('herds')}"
        args: dict[str, Any] = {}
        if herd_ids:
            query += " WHERE " + self._in_clause("herd_id", herd_ids, "herd", args)
        return self.spark.sql(query, args=args)


def to_polars(df: "DataFrame") -> "pl.DataFrame":
    """Collect a Spark `DataFrame` into polars.

    `load_events` returns whatever frame is native to the backend - polars
    from SQLite, Spark from Delta - so this is the bridge when you want a
    Delta result in the same container the local path gives you. It pulls
    the whole result to the driver, so filter and aggregate first.
    """
    import polars as pl

    to_arrow = getattr(df, "toArrow", None)
    if to_arrow is not None:  # Spark 4 / DBR 16+, zero-copy
        return pl.from_arrow(to_arrow())

    try:  # older Spark: via pandas, if it happens to be installed
        return pl.from_pandas(df.toPandas())
    except (ImportError, ModuleNotFoundError):
        # Last resort, so this never hard-fails on a lean environment.
        # Row-at-a-time and slow; another reason to aggregate first.
        return pl.from_dicts([row.asDict(recursive=True) for row in df.collect()])
