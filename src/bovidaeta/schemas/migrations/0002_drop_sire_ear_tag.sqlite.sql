-- Migration 0002: drop Cows.sire_ear_tag (SQLite).
--
-- The column was never filled in. Run after 0001, once per database:
--     sqlite3 dairy_farm.db < 0002_drop_sire_ear_tag.sqlite.sql
-- Needs SQLite 3.35 or newer (2021) for DROP COLUMN. A second run fails
-- ("no such column") and changes nothing.

ALTER TABLE Cows DROP COLUMN sire_ear_tag;
