"""Generate a plausible-looking dummy farm database to develop against.

Run with `python -m bovidaeta.simulation`. Produces a SQLite file in the
format described by `bovidaeta/schemas/sqlite.sql`, readable with
`DairyData.from_sqlite` and loadable into Delta with
`pipelines/sqlite_to_delta.py`.
"""

from .main import Farm, SimConfig

__all__ = ["Farm", "SimConfig"]
