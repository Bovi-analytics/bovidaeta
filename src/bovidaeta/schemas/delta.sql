-- Delta table definitions for bovidaeta data in Databricks Unity Catalog.
--
-- herds/cows mirror the bovidaeta Herd/Cow models directly (stable, low
-- rate of change). Events use a single generic table with a VARIANT
-- metadata column instead of one physical table per event type: new event
-- types and new metadata fields need zero DDL changes this way, since
-- VARIANT absorbs whatever JSON shape a row has. Partitioning by
-- (event_type, event_year) still gives per-event-type query pruning
-- without needing separate tables.
--
-- Run once in a Databricks SQL editor (or `databricks sql query --file ...`).
-- Requires DBR 15.3+ (or a current serverless SQL warehouse) for VARIANT.
--
-- Set the target catalog and schema below first. The tables and views are
-- created there, and the views keep pointing at that schema's `events`
-- table. Pass the same `catalog.schema` to `DairyData.from_delta(...)`.

USE CATALOG bovidaeta;
CREATE SCHEMA IF NOT EXISTS farms;
USE SCHEMA farms;

CREATE TABLE IF NOT EXISTS herds (
  herd_id              STRING NOT NULL,
  source_id            BIGINT,
  name                 STRING,
  data_provider_guid   STRING,
  street               STRING,
  number               STRING,
  registration_number  STRING,
  zip                  STRING,
  city                 STRING,
  state                STRING,
  country              STRING,
  country_code         STRING,
  latitude             DOUBLE,
  longitude            DOUBLE,
  email                STRING,
  mobile_phone_number  STRING,
  telephone_number     STRING,
  CONSTRAINT herds_pk PRIMARY KEY (herd_id)
) USING DELTA;

-- Bridge table: animal_id <-> herd_id. A cow keeps ONE animal_id for life
-- even if it moves between herds/farms, so this can hold more than one row per animal_id.
CREATE TABLE IF NOT EXISTS cows (
  animal_id            STRING NOT NULL,
  herd_id              STRING NOT NULL,
  sire_ear_tag         STRING,
  animal_ear_tag       STRING,
  animal_farm_number   BIGINT,
  animal_legal_id      STRING,
  gender               STRING,
  birth_date           DATE,
  exit_date            DATE,
  born_on_farm         BOOLEAN,
  breed                ARRAY<STRUCT<breed_code: STRING, proportion: DOUBLE>>,
  CONSTRAINT cows_pk PRIMARY KEY (animal_id, herd_id)
) USING DELTA;

CREATE TABLE IF NOT EXISTS events (
  event_id    STRING NOT NULL,
  animal_id   STRING NOT NULL,
  event_type  STRING NOT NULL,
  datetime    TIMESTAMP NOT NULL,
  event_year  INT GENERATED ALWAYS AS (YEAR(datetime)),
  metadata    VARIANT,
  CONSTRAINT events_pk PRIMARY KEY (event_id)
) USING DELTA
PARTITIONED BY (event_type, event_year);

-- Example typed convenience views - free to add/drop as event types come
-- and go, since they cost no storage and need no data migration.
CREATE OR REPLACE VIEW milk_recording_v AS
SELECT
  event_id, animal_id, datetime,
  metadata:lactose_percentage::DOUBLE  AS lactose_percentage,
  metadata:fat_percentage::DOUBLE      AS fat_percentage,
  metadata:protein_percentage::DOUBLE  AS protein_percentage,
  metadata:scc::BIGINT                 AS scc,
  metadata:milking_yield::DOUBLE       AS milking_yield
FROM events
WHERE event_type = 'MilkRecording';

CREATE OR REPLACE VIEW diagnosis_v AS
SELECT
  event_id, animal_id, datetime,
  metadata:disease.disease_code::STRING         AS disease_code,
  metadata:disease.disease_description::STRING  AS disease_description,
  metadata:disease.stage::STRING                AS disease_stage,
  metadata:severity::STRING                     AS severity,
  metadata:diagnosis_method::STRING             AS diagnosis_method,
  metadata:confirmation_status::STRING          AS confirmation_status,
  metadata:diagnostic_source::STRING            AS diagnostic_source,
  metadata:notes::STRING                        AS notes
FROM events
WHERE event_type = 'Diagnosis';
