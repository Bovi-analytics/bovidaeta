import os
import sqlite3
from datetime import datetime
from typing import Iterable, Optional

import polars as pl
from dotenv import load_dotenv

load_dotenv()


class FarmEventData:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            db_path = os.environ["DB_PATH"]
        self.db_uri = f"file:{db_path}?mode=ro"

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
                select_cols.append(f"metadata ->> '$.{key}' AS {key}")
        else:
            select_cols.append("metadata")

        query = f"SELECT {', '.join(select_cols)} FROM Events"
        conditions = []
        params = []

        # Build dynamic WHERE clauses
        if dts_start:
            conditions.append("datetime >= ?")
            params.append(dts_start.isoformat())

        if dts_end:
            conditions.append("datetime <= ?")
            params.append(dts_end.isoformat())

        if subset_events:
            events_tuple = tuple(subset_events)
            conditions.append(f"event_type IN ({','.join(['?'] * len(events_tuple))})")
            params.extend(events_tuple)

        if subset_cows:
            cows_tuple = tuple(subset_cows)
            conditions.append(f"animal_id IN ({','.join(['?'] * len(cows_tuple))})")
            params.extend(cows_tuple)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        with sqlite3.connect(self.db_uri, uri=True) as conn:
            df = pl.read_database(
                query=query, connection=conn, execute_options={"parameters": params}
            )
            return df.lazy()
