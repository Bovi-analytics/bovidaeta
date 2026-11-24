-- Migration 0002: drop cows.sire_ear_tag (Delta / Unity Catalog).
--
-- The column was never filled in. Run after 0001: set the catalog and schema
-- below, then run once in a Databricks SQL editor.
--
-- Delta can only drop a column from a table with column mapping enabled, so
-- that is switched on first. This upgrades the table's Delta protocol
-- (reader 2 / writer 5): fine for Databricks Runtime 10.4+ and current Spark
-- Delta readers, but older readers can no longer read `cows`. Dropping is a
-- metadata-only change; the data files are not rewritten.

USE CATALOG bovidaeta;
USE SCHEMA farms;

ALTER TABLE cows SET TBLPROPERTIES ('delta.columnMapping.mode' = 'name');

ALTER TABLE cows DROP COLUMN sire_ear_tag;
