import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

import polars as pl

from ..enums import EventType


class FarmData:
    def __init__(self, db_path="/data/dairy_farm.db"):
        self.db_path = Path(db_path)

    def load_events(
        self,
        dts_start: datetime | None = None,
        dts_end: datetime | None = None,
        subset_events: Iterable[EventType | str] | None = None,
        subset_metadata: Iterable[str] | None = None,
        subset_cows: Iterable[str] | None = None,
    ) -> pl.DataFrame:

        select_cols = ["event_id", "animal_id", "event_type", "datetime"]
        if subset_metadata:
            for key in subset_metadata:
                select_cols.append(f"json_extract(metadata, '$.{key}') AS {key}")
        else:
            select_cols.append("metadata")

        query = f"SELECT {', '.join(select_cols)} FROM events"

        conditions = []
        params = []

        if dts_start:
            conditions.append("datetime >= ?")
            params.append(dts_start.isoformat(sep=" "))

        if dts_end:
            conditions.append("datetime <= ?")
            params.append(dts_end.isoformat(sep=" "))

        if subset_events:
            events_list = [e.value if isinstance(e, EventType) else e for e in subset_events]
            placeholders = ", ".join(["?"] * len(events_list))
            conditions.append(f"event_type IN ({placeholders})")
            params.extend(events_list)

        if subset_cows:
            cows_list = list(subset_cows)
            placeholders = ", ".join(["?"] * len(cows_list))
            conditions.append(f"animal_id IN ({placeholders})")
            params.extend(cows_list)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA busy_timeout = 5000;")
            df = pl.read_database(
                query=query, connection=conn, execute_options={"parameters": params}
            )

            return df
