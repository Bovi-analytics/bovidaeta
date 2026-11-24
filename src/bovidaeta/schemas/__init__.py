"""Canonical DDL for both storage backends, shipped with the package.

`sqlite.sql` is executed by the simulator to create a farm database, and
describes what `DairyData.from_sqlite` expects to read. `delta.sql`
is run once by hand in a Databricks SQL editor, and describes what
`DairyData.from_delta` expects to read.

`migrations/` holds the SQL that brings a database created with an older
version of these files up to date; see `README.md` next to this file.

Keeping them here rather than at the repo root means they travel with an
installed copy of the package, so `read_schema()` works from anywhere.
"""

from importlib.resources import files

__all__ = [
    "DELTA_SCHEMA",
    "DELTA_STUDIES_MIGRATION",
    "SQLITE_SCHEMA",
    "SQLITE_STUDIES_MIGRATION",
    "read_schema",
]

SQLITE_SCHEMA = "sqlite.sql"
DELTA_SCHEMA = "delta.sql"

# Adds studies (Studies/StudyAnimals tables, AnimalEvents.study_id).
SQLITE_STUDIES_MIGRATION = "migrations/0001_studies.sqlite.sql"
DELTA_STUDIES_MIGRATION = "migrations/0001_studies.delta.sql"


def read_schema(name: str = SQLITE_SCHEMA) -> str:
    """Return the text of one of the bundled schema or migration files."""
    resource = files(__package__)
    for part in name.split("/"):
        resource = resource.joinpath(part)
    return resource.read_text(encoding="utf-8")
