import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

import polars as pl


class FarmEventData:
    def __init__(self):
        self.data_dir = Path.home() / "nsf-data"

    def load(
        self,
        dts_start: Optional[datetime] = None,
        dts_end: Optional[datetime] = None,
        subset_events: Optional[Iterable[str]] = None,
        subset_metadata: Optional[Iterable[str]] = None,
        subset_cows: Optional[Iterable[str]] = None,
    ) -> pl.LazyFrame:

        lf = pl.scan_parquet(
            os.path.join(self.data_dir, "**/*.parquet"), hive_partitioning=True
        )
        lf = lf.with_columns(pl.col("datetime").str.to_datetime(time_zone="UTC"))

        if dts_start:
            # Prune directories
            prune_start = (pl.col("year") > dts_start.year) | (
                (pl.col("year") == dts_start.year)
                & (pl.col("month") >= dts_start.month)
            )
            lf = lf.filter(prune_start)
            # Exact datetime filter
            lf = lf.filter(pl.col("datetime") >= dts_start)

        if dts_end:
            # Prune directories
            prune_end = (pl.col("year") < dts_end.year) | (
                (pl.col("year") == dts_end.year) & (pl.col("month") <= dts_end.month)
            )
            lf = lf.filter(prune_end)
            # Exact datetime filter
            lf = lf.filter(pl.col("datetime") <= dts_end)

        if subset_events:
            lf = lf.filter(pl.col("event_type").is_in(list(subset_events)))

        if subset_cows:
            lf = lf.filter(pl.col("animal_id").is_in(list(subset_cows)))

        select_cols = [
            pl.col("event_id"),
            pl.col("animal_id"),
            pl.col("event_type"),
            pl.col("datetime"),
        ]

        if subset_metadata:
            for key in subset_metadata:
                expr = pl.col("metadata").struct.field(key).alias(key)
                select_cols.append(expr)
        else:
            select_cols.append(pl.col("metadata"))

        return lf.select(select_cols)
