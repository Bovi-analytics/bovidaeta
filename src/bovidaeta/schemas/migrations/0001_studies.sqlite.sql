-- Migration 0001: research studies (SQLite).
--
-- Brings a database created before studies were added up to the current
-- `sqlite.sql`: adds the Studies and StudyAnimals tables and the nullable
-- AnimalEvents.study_id column. Existing rows get study_id NULL, which is
-- what farm data has, so a migrated database loads exactly as before.
--
-- Run once per database, for example:
--     sqlite3 dairy_farm.db < 0001_studies.sqlite.sql
-- A second run fails on the ALTER TABLE ("duplicate column name: study_id")
-- and changes nothing; that is how to tell a database is already migrated.

BEGIN;

ALTER TABLE AnimalEvents ADD COLUMN study_id TEXT;

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

CREATE TABLE IF NOT EXISTS StudyAnimals (
    study_id    TEXT NOT NULL,
    animal_id   TEXT NOT NULL,
    study_group TEXT,
    PRIMARY KEY (study_id, animal_id)
);

COMMIT;
