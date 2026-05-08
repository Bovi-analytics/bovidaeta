from collections.abc import Iterable
from datetime import datetime
from pathlib import Path


class FarmEventData:
    def __init__(self, data_dir="/data/parquet"):
        self.data_dir = Path(data_dir)

    def load(
        self,
        dts_start: datetime | None = None,
        dts_end: datetime | None = None,
        subset_events: Iterable[str] | None = None,
        subset_metadata: Iterable[str] | None = None,
        subset_cows: Iterable[str] | None = None,
    ) -> "pl.DataFrame":

        import polars as pl
        import pyarrow.compute as pc
        import pyarrow.dataset as ds

        dataset = ds.dataset(self.data_dir, format="parquet", partitioning="hive")

        filters = []
        if dts_start:
            filters.append(pc.field("datetime") >= dts_start)
        if dts_end:
            filters.append(pc.field("datetime") <= dts_end)
        if subset_events:
            filters.append(pc.field("event_type").isin(list(subset_events)))
        if subset_cows:
            filters.append(pc.field("animal_id").isin(list(subset_cows)))

        combined_filter = None
        if filters:
            combined_filter = filters[0]
            for f in filters[1:]:
                combined_filter = combined_filter & f

        base_cols = ["event_id", "animal_id", "event_type", "datetime", "metadata"]

        table = dataset.to_table(columns=base_cols, filter=combined_filter)

        df = pl.DataFrame(table)

        df = df.with_columns(pl.col("datetime").cast(pl.Datetime(time_zone="UTC")))

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

        return df.select(select_cols)
