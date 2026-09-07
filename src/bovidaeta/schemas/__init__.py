"""Canonical DDL for both storage backends, shipped with the package.

`sqlite.sql` is executed by the simulator to create a farm database, and
describes what `DairyData.from_sqlite` expects to read. `delta.sql`
is run once by hand in a Databricks SQL editor, and describes what
`DairyData.from_delta` expects to read.

Keeping them here rather than at the repo root means they travel with an
installed copy of the package, so `read_schema()` works from anywhere.
"""

from importlib.resources import files

__all__ = ["DELTA_SCHEMA", "SQLITE_SCHEMA", "read_schema"]

SQLITE_SCHEMA = "sqlite.sql"
DELTA_SCHEMA = "delta.sql"


def read_schema(name: str = SQLITE_SCHEMA) -> str:
    """Return the text of one of the bundled schema files."""
    return files(__package__).joinpath(name).read_text(encoding="utf-8")
