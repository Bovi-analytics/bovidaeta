import os
from datetime import datetime
from typing import Iterable, Optional

import polars as pl
import psycopg
from dotenv import load_dotenv

load_dotenv()


class FarmEventData:
    def __init__(self):
        self.db_uri = os.environ["DB_TIMELINE_URI"]

    def load(
        self,
        dts_start: Optional[datetime] = None,
        dts_end: Optional[datetime] = None,
        subset_events: Optional[Iterable[str]] = None,
        subset_metadata: Optional[Iterable[str]] = None,
        subset_cows: Optional[Iterable[str]] = None,
    ) -> pl.LazyFrame:

        select_cols = ["event_id", "animal_id", "event_type", "datetime"]

        if subset_metadata:
            for key in subset_metadata:
                select_cols.append(f"metadata ->> '{key}' AS {key}")
        else:
            select_cols.append("metadata")

        query = f"SELECT {', '.join(select_cols)} FROM Events"
        conditions = []
        params = []

        if dts_start:
            conditions.append("datetime >= %s")
            params.append(dts_start)

        if dts_end:
            conditions.append("datetime <= %s")
            params.append(dts_end)

        if subset_events:
            events_tuple = tuple(subset_events)
            conditions.append(f"event_type IN ({','.join(['%s'] * len(events_tuple))})")
            params.extend(events_tuple)

        if subset_cows:
            cows_tuple = tuple(subset_cows)
            conditions.append(f"animal_id IN ({','.join(['%s'] * len(cows_tuple))})")
            params.extend(cows_tuple)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Connect using psycopg3 and enforce read-only
        with psycopg.connect(self.db_uri) as conn:
            conn.read_only = True
            df = pl.read_database(
                query=query, connection=conn, execute_options={"params": params}
            )
            return df.lazy()
