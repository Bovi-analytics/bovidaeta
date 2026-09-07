-- SQLite schema for a single farm's event store.
--
-- This is the on-farm / edge format: one database file per farm, holding
-- only that farm's data. `DairyData.from_sqlite` reads it, and
-- `bovidaeta.simulation` creates it (see `Farm.setup_db`, which executes
-- this file verbatim).
--
-- Metadata is stored as a JSON TEXT column rather than as typed columns,
-- for the same reason the Delta `events` table uses VARIANT: a new event
-- type or a new metadata field needs no migration. `json_extract` pulls
-- individual keys back out as columns at query time.
--
-- The cloud-side counterpart is `delta.sql`. The two differ in two ways
-- worth knowing about:
--   * Delta `cows` flattens the cow metadata into typed columns, while
--     here it stays a JSON blob.
--   * Delta `events` has no herd column; herd membership is resolved
--     through the `cows` bridge table, since one animal_id can appear in
--     more than one herd over its life. On a single farm that question
--     rarely arises, but `Cows.herd_id` answers it the same way.
--   * Delta `herds` carries full address and contact columns. A farm
--     export only ever populates the three below, so that is all this
--     table holds.

CREATE TABLE IF NOT EXISTS Herds (
    herd_id      TEXT PRIMARY KEY,
    source_id    INTEGER NOT NULL,
    country_code TEXT
);

CREATE TABLE IF NOT EXISTS Events (
    event_id   TEXT PRIMARY KEY,
    datetime   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    animal_id  TEXT NOT NULL,
    metadata   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Cows (
    animal_id    TEXT PRIMARY KEY,
    herd_id      TEXT NOT NULL,
    sire_ear_tag TEXT,
    metadata     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type_dts   ON Events (event_type, datetime);
CREATE INDEX IF NOT EXISTS idx_events_animal_dts ON Events (animal_id, datetime);
