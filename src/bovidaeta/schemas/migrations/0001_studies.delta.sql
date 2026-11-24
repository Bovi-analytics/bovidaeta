-- Migration 0001: research studies (Delta / Unity Catalog).
--
-- Brings tables created before studies were added up to the current
-- `delta.sql`: adds the studies and study_animals tables and the nullable
-- animal_events.study_id column. Existing rows read study_id as NULL, which
-- is what farm data has, so a migrated schema loads exactly as before.
-- Adding a column is a metadata-only change: no data files are rewritten.
--
-- Set the catalog and schema below to the ones you created with `delta.sql`,
-- then run once in a Databricks SQL editor. A second run fails on the
-- ALTER TABLE (the column already exists) and changes nothing.

USE CATALOG bovidaeta;
USE SCHEMA farms;

ALTER TABLE animal_events ADD COLUMN study_id STRING
  COMMENT 'The study that recorded the event, NULL for farm data';

CREATE TABLE IF NOT EXISTS studies (
  study_id             STRING NOT NULL,
  project              STRING,
  name                 STRING,
  description          STRING,
  start_date           DATE,
  end_date             DATE,
  doi_or_protocol_url  STRING,
  open_data            BOOLEAN,
  license              STRING,
  credit_required      BOOLEAN,
  contributors         STRING,
  CONSTRAINT studies_pk PRIMARY KEY (study_id)
) USING DELTA;

CREATE TABLE IF NOT EXISTS study_animals (
  study_id     STRING NOT NULL,
  animal_id    STRING NOT NULL,
  study_group  STRING,
  CONSTRAINT study_animals_pk PRIMARY KEY (study_id, animal_id)
) USING DELTA;
