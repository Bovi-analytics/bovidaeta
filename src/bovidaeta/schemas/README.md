# Schemas

The table definitions for both stores, shipped with the package
(`bovidaeta.schemas.read_schema(name)` returns any of these files):

- [`sqlite.sql`](sqlite.sql): one farm's database, read by
  `DairyData.from_sqlite`. The simulator and the edge data API create
  databases from it.
- [`delta.sql`](delta.sql): the multi-farm Delta tables in Unity Catalog,
  read by `DairyData.from_delta`. Run once in a Databricks SQL editor.
- [`migrations/`](migrations): SQL that brings a database created with an
  older version of these files up to date.

## Tables

| SQLite         | Delta           | Holds                                                     |
| -------------- | --------------- | --------------------------------------------------------- |
| `Herds`        | `herds`         | herds                                                     |
| `Cows`         | `cows`          | cows, and which herd they are in                          |
| `AnimalEvents` | `animal_events` | every event, with its metadata as JSON / `VARIANT`        |
| `Studies`      | `studies`       | research studies (empty for farm data)                    |
| `StudyAnimals` | `study_animals` | which animals took part in which study, and in what group |

`AnimalEvents.study_id` is the study that recorded an event, and null for
farm data. An animal keeps one `animal_id` across studies, so it can be in
several: `StudyAnimals` has a row per (study, animal).

## Migrating existing databases

`CREATE TABLE IF NOT EXISTS` does not change a table that already exists, so
re-running `sqlite.sql` or `delta.sql` is not enough when they gain a column.
Run each migration newer than your database once, in order. The loader
expects the current schema and does not work around missing tables or
columns.

| Migration | Adds                                                                                     |
| --------- | ---------------------------------------------------------------------------------------- |
| `0001_studies` | `Studies` / `StudyAnimals` tables and `AnimalEvents.study_id` (Delta: `studies`, `study_animals`, `animal_events.study_id`) |

Existing rows get a null `study_id`, which is what farm data has, so a
migrated database loads exactly as before, with an extra (null) `study_id`
column. A database is already migrated when it has the column; running the
migration a second time fails on the `ALTER TABLE` and changes nothing.

### SQLite

From a shell, with the `sqlite3` CLI:

```bash
sqlite3 dairy_farm.db < src/bovidaeta/schemas/migrations/0001_studies.sqlite.sql
```

Or from Python, using the copy that ships with the package:

```python
import sqlite3

from bovidaeta.schemas import SQLITE_STUDIES_MIGRATION, read_schema

with sqlite3.connect("dairy_farm.db") as conn:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(AnimalEvents)")}
    if "study_id" not in columns:
        conn.executescript(read_schema(SQLITE_STUDIES_MIGRATION))
```

The SQL, for reference:

```sql
ALTER TABLE AnimalEvents ADD COLUMN study_id TEXT;
CREATE TABLE IF NOT EXISTS Studies (
    study_id TEXT PRIMARY KEY, project TEXT, name TEXT, description TEXT,
    start_date TEXT, end_date TEXT, doi_or_protocol_url TEXT,
    open_data INTEGER NOT NULL DEFAULT 0, license TEXT, credit_required INTEGER,
    contributors TEXT
);
CREATE TABLE IF NOT EXISTS StudyAnimals (
    study_id TEXT NOT NULL, animal_id TEXT NOT NULL, study_group TEXT,
    PRIMARY KEY (study_id, animal_id)
);
```

### Delta

Set the catalog and schema at the top of
[`migrations/0001_studies.delta.sql`](migrations/0001_studies.delta.sql),
then run it in a Databricks SQL editor. Adding a column is a metadata-only
change; no data files are rewritten.

```sql
USE CATALOG bovidaeta;
USE SCHEMA farms;

ALTER TABLE animal_events ADD COLUMN study_id STRING;
-- then the CREATE TABLE statements for `studies` and `study_animals`,
-- as in delta.sql
```

## Changing a schema

Change `sqlite.sql` and `delta.sql` together, add new columns at the end of
a table (that is where `ALTER TABLE ... ADD COLUMN` puts them, so new and
migrated databases match), and add a numbered migration for both stores.
`tests/test_studies.py` shows how to check a migrated database against a new
one.
