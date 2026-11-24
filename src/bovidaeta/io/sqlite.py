"""SQLite backend: one farm's local database.

This is the on-farm / edge path - a single `.db` file holding one farm's
data, read with nothing but the standard library and polars. Reached
through `DairyData.from_sqlite(...)`, not used directly.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import polars as pl

from .base import (
    BASE_COLUMNS,
    CAST_TYPES,
    STUDY_ANIMAL_COLUMNS,
    STUDY_COLUMNS,
    EventBackend,
)

# Polars type for each `subset_metadata` cast (see CAST_TYPES). DATE and
# TIMESTAMP stay text: that is how SQLite stores them.
_CAST_DTYPES: dict[str, pl.DataType] = {
    "STRING": pl.String,
    "BOOLEAN": pl.Int64,
    "INT": pl.Int64,
    "BIGINT": pl.Int64,
    "FLOAT": pl.Float64,
    "DOUBLE": pl.Float64,
    "DECIMAL": pl.Float64,
    "DATE": pl.String,
    "TIMESTAMP": pl.String,
}


class _SQLiteBackend(EventBackend):
    name = "sqlite"

    def __init__(
        self, db_path: str | Path = "/data/dairy_farm.db", immutable: bool = False
    ):
        self.db_path = Path(db_path)
        self.immutable = immutable

    def __repr__(self) -> str:
        suffix = ":immutable" if self.immutable else ""
        return f"sqlite:{self.db_path}{suffix}"

    def _connect(self) -> sqlite3.Connection:
        """Open the database. Read-only by pragma, not by file mode.

        A database in WAL mode is read through its `-shm` wal-index, which a
        reader has to be able to create and lock — so even a pure reader needs
        write access to the file and its directory. Asking for `mode=ro`
        instead fails outright there, and `immutable=1` succeeds only by
        promising SQLite the file never changes, which means skipping the WAL
        and all locking: against a database something else is writing, that
        returns whatever half-written pages happen to be on disk, silently.

        `PRAGMA query_only` is what actually makes this connection read-only.
        It refuses every write on the connection itself, without lying to
        SQLite about the file.
        """
        if self.immutable:
            # Only for a file that genuinely cannot change: a frozen snapshot,
            # or one on read-only media where the sidecars cannot be created.
            uri = f"file:{quote(str(self.db_path))}?mode=ro&immutable=1"
            return sqlite3.connect(uri, uri=True)

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA query_only = 1;")
        return conn

    def _query(
        self,
        query: str,
        params: list[str],
        schema: dict[str, pl.DataType] | None = None,
    ) -> pl.DataFrame:
        """Run a query into a frame.

        The driver hands rows over as Python values, and by default polars
        guesses each column's type from the first 100. A metadata key that is
        null in those (say `milk_date` on events from before it was recorded)
        and set further down then fails the whole read, so the types the
        caller knows are passed as `schema`, and the rest are inferred from
        every row.
        """
        conn = self._connect()
        try:
            conn.execute("PRAGMA busy_timeout = 5000;")
            df = pl.read_database(
                query=query,
                connection=conn,
                execute_options={"parameters": params},
                schema_overrides=schema,
                infer_schema_length=None,
            )
        finally:
            conn.close()

        # Ensure down-stream code doesn't crash when trying to use an empty frame
        if df.height == 0:
            df = df.cast(
                {
                    name: pl.String
                    for name, dtype in df.schema.items()
                    if dtype == pl.Null
                }
            )
        return df

    @staticmethod
    def _in_clause(column: str, values: list[str], params: list[str]) -> str:
        params.extend(values)
        return f"{column} IN ({', '.join(['?'] * len(values))})"

    @staticmethod
    def _metadata_projection(metadata: dict[str, str | None]) -> list[str]:
        """`json_extract(metadata, '$.key') AS key`, optionally cast.

        SQLite's `json_extract` is untyped and polars infers a type per
        column, so a cast is usually unnecessary here. It is accepted
        anyway, and translated to the SQLite type, so that the same
        `subset_metadata` mapping works against either backend.
        """
        cols = []
        for key, cast in metadata.items():
            expr = f"json_extract(metadata, '$.{key}')"
            if cast:
                expr = f"CAST({expr} AS {CAST_TYPES[cast]})"
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
        study_ids: list[str] | None,
    ) -> pl.DataFrame:
        select_cols = list(BASE_COLUMNS)
        if metadata:
            select_cols += self._metadata_projection(metadata)
        else:
            select_cols.append("metadata")

        conditions: list[str] = []
        params: list[str] = []

        if dts_start:
            conditions.append("datetime >= ?")
            params.append(dts_start.isoformat(sep=" "))
        if dts_end:
            conditions.append("datetime <= ?")
            params.append(dts_end.isoformat(sep=" "))
        if event_types:
            conditions.append(self._in_clause("event_type", event_types, params))
        if cow_ids:
            conditions.append(self._in_clause("animal_id", cow_ids, params))
        if herd_ids:
            # AnimalEvents carry no herd column; membership lives on Cows. One
            # file usually holds one herd, so this is rarely needed - it
            # exists so the argument means the same thing on both backends.
            herd_filter = self._in_clause("herd_id", herd_ids, params)
            conditions.append(
                f"animal_id IN (SELECT animal_id FROM Cows WHERE {herd_filter})"
            )
        if study_ids:
            conditions.append(self._in_clause("study_id", study_ids, params))

        query = f"SELECT {', '.join(select_cols)} FROM AnimalEvents"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        schema = {col: pl.String for col in BASE_COLUMNS}
        schema |= {
            key: _CAST_DTYPES[cast] for key, cast in (metadata or {}).items() if cast
        }
        return self._query(query, params, schema)

    def load_cows(
        self,
        cow_ids: list[str] | None,
        herd_ids: list[str] | None,
        farm_numbers: list[int] | None,
    ) -> pl.DataFrame:
        conditions: list[str] = []
        params: list = []
        if cow_ids:
            conditions.append(self._in_clause("animal_id", cow_ids, params))
        if herd_ids:
            conditions.append(self._in_clause("herd_id", herd_ids, params))
        if farm_numbers:
            # Cow attributes live in the JSON `metadata` column. Cows is one row
            # per animal, so scanning it is cheap and needs no index.
            conditions.append(
                self._in_clause(
                    "json_extract(metadata, '$.animal_farm_number')",
                    farm_numbers,
                    params,
                )
            )

        query = "SELECT animal_id, herd_id, sire_ear_tag, metadata FROM Cows"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        return self._query(query, params)

    def load_herds(self, herd_ids: list[str] | None) -> pl.DataFrame:
        query = "SELECT herd_id, source_id, country_code FROM Herds"
        params: list[str] = []
        if herd_ids:
            query += " WHERE " + self._in_clause("herd_id", herd_ids, params)
        return self._query(query, params)

    def load_studies(self, study_ids: list[str] | None) -> pl.DataFrame:
        query = f"SELECT {', '.join(STUDY_COLUMNS)} FROM Studies"
        params: list[str] = []
        if study_ids:
            query += " WHERE " + self._in_clause("study_id", study_ids, params)
        # SQLite keeps booleans as 0/1; return them as booleans, like Delta.
        flags = ("open_data", "credit_required")
        schema = {col: pl.String for col in STUDY_COLUMNS}
        schema |= {col: pl.Int64 for col in flags}
        df = self._query(query, params, schema)
        return df.with_columns(pl.col(*flags).cast(pl.Boolean))

    def load_study_animals(self, study_ids: list[str] | None) -> pl.DataFrame:
        query = f"SELECT {', '.join(STUDY_ANIMAL_COLUMNS)} FROM StudyAnimals"
        params: list[str] = []
        if study_ids:
            query += " WHERE " + self._in_clause("study_id", study_ids, params)
        schema = {col: pl.String for col in STUDY_ANIMAL_COLUMNS}
        return self._query(query, params, schema)
