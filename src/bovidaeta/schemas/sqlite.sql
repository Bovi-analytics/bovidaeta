-- SQLite schema for a single farm's event store.
--
-- This is the on-farm / edge format: one database file per farm, holding
-- only that farm's data. `DairyData.from_sqlite` reads it, and
-- `bovidaeta.simulation` creates it (see `Farm.setup_db`, which executes
-- this file verbatim).
--
-- Metadata is stored as a JSON TEXT column rather than as typed columns,
-- for the same reason the Delta `animal_events` table uses VARIANT: a new event
-- type or a new metadata field needs no migration. `json_extract` pulls
-- individual keys back out as columns at query time.
--
-- The cloud-side counterpart is `delta.sql`. The two differ in two ways
-- worth knowing about:
--   * Delta `cows` flattens the cow metadata into typed columns, while
--     here it stays a JSON blob.
--   * Delta `animal_events` has no herd column; herd membership is resolved
--     through the `cows` bridge table, since one animal_id can appear in
--     more than one herd over its life. On a single farm that question
--     rarely arises, but `Cows.herd_id` answers it the same way.
--   * Delta `herds` carries full address and contact columns. A farm
--     export only ever populates the three below, so that is all this
--     table holds.
--
-- Studies / StudyAnimals hold research-study data (see `bovidaeta.Study`)
-- and are empty for farm data, as is `AnimalEvents.study_id`.
--
-- Changing this file? Existing databases are not recreated, so ship a
-- migration in `migrations/` as well (see the README next to this file).

CREATE TABLE IF NOT EXISTS Herds (
    herd_id      TEXT PRIMARY KEY,
    source_id    INTEGER NOT NULL,
    country_code TEXT
);

-- Events about a single animal (Delta: `animal_events`). Named AnimalEvents so that
-- events not tied to an animal can get a table of their own later.
CREATE TABLE IF NOT EXISTS AnimalEvents (
    event_id   TEXT PRIMARY KEY,
    datetime   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    animal_id  TEXT NOT NULL,
    metadata   TEXT NOT NULL,
    -- The study that recorded the event; NULL for farm data. Last, so that a
    -- new database has the same column order as a migrated one.
    study_id   TEXT
);

CREATE TABLE IF NOT EXISTS Cows (
    animal_id    TEXT PRIMARY KEY,
    herd_id      TEXT NOT NULL,
    metadata     TEXT NOT NULL
);

-- Research studies. Empty for farm data. Dates are ISO-8601 text, booleans
-- 0/1, as elsewhere in SQLite.
CREATE TABLE IF NOT EXISTS Studies (
    study_id            TEXT PRIMARY KEY,
    project             TEXT,
    name                TEXT,
    description         TEXT,
    start_date          TEXT,
    end_date            TEXT,
    doi_or_protocol_url TEXT,
    open_data           INTEGER NOT NULL DEFAULT 0,
    license             TEXT,
    credit_required     INTEGER,
    contributors        TEXT
);

-- Which animals took part in which study. An animal can be in several.
CREATE TABLE IF NOT EXISTS StudyAnimals (
    study_id    TEXT NOT NULL,
    animal_id   TEXT NOT NULL,
    study_group TEXT,
    PRIMARY KEY (study_id, animal_id)
);

-- There is deliberately no index on AnimalEvents.study_id: this file is also
-- run against existing databases (CREATE ... IF NOT EXISTS), and an index on
-- a column a not-yet-migrated database lacks would make that fail.

-- The index names date from when the table was called Events. They are kept,
-- so a database migrated with `ALTER TABLE Events RENAME TO AnimalEvents`
-- (which keeps its indexes) doesn't get every index built a second time.
CREATE INDEX IF NOT EXISTS idx_events_type_dts   ON AnimalEvents (event_type, datetime);
CREATE INDEX IF NOT EXISTS idx_events_animal_dts ON AnimalEvents (animal_id, datetime);
