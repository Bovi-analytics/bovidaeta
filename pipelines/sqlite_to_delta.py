# Databricks notebook source
# MAGIC %md
# MAGIC ## Load per-farm SQLite exports into Delta tables
# MAGIC
# MAGIC Run `bovidaeta/schemas/delta.sql` once first to create the tables. This notebook reads
# MAGIC every `dairy_farm_*.db` file (one per farm, see export_all_farms.py)
# MAGIC from a folder already uploaded to the volume, and appends each farm's
# MAGIC `Herds` / `Cows` / `AnimalEvents` / `Studies` / `StudyAnimals` rows (the
# MAGIC study tables, and `AnimalEvents.study_id`, are empty for farm data).
# MAGIC Every file must have the current schema: migrate older ones first with
# MAGIC `bovidaeta/schemas/migrations/`. Events keep their raw JSON metadata,
# MAGIC parsed into the `animal_events` table's VARIANT column - no per-event-type
# MAGIC handling needed, a new event type just flows through as-is.
# MAGIC
# MAGIC The SQLite side of this is the format described by
# MAGIC `bovidaeta/schemas/sqlite.sql`; the Delta side is
# MAGIC `bovidaeta/schemas/delta.sql`. Point `farms_dir` at a volume
# MAGIC folder of `dairy_farm_*.db` files and `catalog_schema` at the
# MAGIC target - nothing here is specific to one dataset.
# MAGIC
# MAGIC Explicit schemas are passed to every `createDataFrame` call below.
# MAGIC Spark infers a schema from the data when none is given, and it can't
# MAGIC infer a type for a column that is `None` in every single row - which
# MAGIC happens here, since some source datasets never set several optional cow
# MAGIC fields (`birth_date`, `breed`, ...). That's the
# MAGIC `CANNOT_DETERMINE_TYPE` error; passing the target table's schema
# MAGIC directly sidesteps inference entirely, and also means every farm's
# MAGIC file gets read with the exact same schema and types.
# MAGIC
# MAGIC First-load only (plain append, not a MERGE) - future incremental loads
# MAGIC for new/updated farms should switch to a MERGE on the primary keys.

# COMMAND ----------

from datetime import date
from pathlib import Path

from pyspark.sql.functions import expr, to_timestamp
from pyspark.sql.types import (
    ArrayType,
    BooleanType,
    DateType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
)

dbutils.widgets.text("farms_dir", "/Volumes/bovidaeta/farms/files/farms")
dbutils.widgets.text("catalog_schema", "bovidaeta.farms")

FARMS_DIR = Path(dbutils.widgets.get("farms_dir"))
CATALOG_SCHEMA = dbutils.widgets.get("catalog_schema")
BATCH_SIZE = 500_000

# Mirrors schema.sql's herds/cows tables exactly. Any key a source row is
# missing (some source herds only ever populate herd_id/source_id/country_code)
# is filled with null automatically - createDataFrame looks fields up by name.
HERD_SCHEMA = StructType(
    [
        StructField("herd_id", StringType(), False),
        StructField("source_id", LongType(), True),
        StructField("name", StringType(), True),
        StructField("data_provider_guid", StringType(), True),
        StructField("street", StringType(), True),
        StructField("number", StringType(), True),
        StructField("registration_number", StringType(), True),
        StructField("zip", StringType(), True),
        StructField("city", StringType(), True),
        StructField("state", StringType(), True),
        StructField("country", StringType(), True),
        StructField("country_code", StringType(), True),
        StructField("latitude", DoubleType(), True),
        StructField("longitude", DoubleType(), True),
        StructField("email", StringType(), True),
        StructField("mobile_phone_number", StringType(), True),
        StructField("telephone_number", StringType(), True),
    ]
)

COW_SCHEMA = StructType(
    [
        StructField("animal_id", StringType(), False),
        StructField("herd_id", StringType(), False),
        StructField("animal_ear_tag", StringType(), True),
        StructField("animal_farm_number", LongType(), True),
        StructField("animal_legal_id", StringType(), True),
        StructField("gender", StringType(), True),
        StructField("birth_date", DateType(), True),
        StructField("exit_date", DateType(), True),
        StructField("born_on_farm", BooleanType(), True),
        StructField(
            "breed",
            ArrayType(
                StructType(
                    [
                        StructField("breed_code", StringType(), True),
                        StructField("proportion", DoubleType(), True),
                    ]
                )
            ),
            True,
        ),
    ]
)

STUDY_SCHEMA = StructType(
    [
        StructField("study_id", StringType(), False),
        StructField("project", StringType(), True),
        StructField("name", StringType(), True),
        StructField("description", StringType(), True),
        StructField("start_date", DateType(), True),
        StructField("end_date", DateType(), True),
        StructField("doi_or_protocol_url", StringType(), True),
        StructField("open_data", BooleanType(), True),
        StructField("license", StringType(), True),
        StructField("credit_required", BooleanType(), True),
        StructField("contributors", StringType(), True),
    ]
)

STUDY_ANIMAL_SCHEMA = StructType(
    [
        StructField("study_id", StringType(), False),
        StructField("animal_id", StringType(), False),
        StructField("study_group", StringType(), True),
    ]
)

# datetime stays a string here and is cast with to_timestamp() below, rather
# than typed as TimestampType up front - Spark won't auto-parse a string into
# a TimestampType column when a schema is enforced (unlike schema inference).
EVENT_SCHEMA = StructType(
    [
        StructField("event_id", StringType(), False),
        StructField("animal_id", StringType(), False),
        StructField("event_type", StringType(), False),
        StructField("datetime", StringType(), False),
        StructField("metadata", StringType(), True),
        StructField("study_id", StringType(), True),
    ]
)

# COMMAND ----------

import json
import sqlite3

db_paths = sorted(FARMS_DIR.glob("dairy_farm_*.db"))
print(f"found {len(db_paths)} farm files in {FARMS_DIR}")

# COMMAND ----------


def cow_row(row: sqlite3.Row) -> dict:
    meta = json.loads(row["metadata"])
    return {
        "animal_id": row["animal_id"],
        "herd_id": row["herd_id"],
        "animal_ear_tag": meta.get("animal_ear_tag"),
        "animal_farm_number": meta.get("animal_farm_number"),
        "animal_legal_id": meta.get("animal_legal_id"),
        "gender": meta.get("gender"),
        "birth_date": meta.get("birth_date"),
        "exit_date": meta.get("exit_date"),
        "born_on_farm": meta.get("born_on_farm"),
        "breed": meta.get("breed"),
    }


def study_row(row: sqlite3.Row) -> dict:
    # SQLite keeps dates as ISO text and booleans as 0/1.
    out = dict(row)
    for key in ("start_date", "end_date"):
        out[key] = date.fromisoformat(out[key]) if out[key] else None
    for key in ("open_data", "credit_required"):
        out[key] = None if out[key] is None else bool(out[key])
    return out


def append(rows: list[dict], schema: StructType, table: str) -> None:
    if rows:  # Studies and StudyAnimals are empty for farm data
        spark.createDataFrame(rows, schema=schema).write.format("delta").mode(
            "append"
        ).saveAsTable(f"{CATALOG_SCHEMA}.{table}")


def load_farm(db_path: Path) -> tuple[int, int, int]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    herds = [dict(row) for row in conn.execute("SELECT * FROM Herds")]
    spark.createDataFrame(herds, schema=HERD_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(f"{CATALOG_SCHEMA}.herds")

    cows = [cow_row(row) for row in conn.execute("SELECT * FROM Cows")]
    spark.createDataFrame(cows, schema=COW_SCHEMA).write.format("delta").mode(
        "append"
    ).saveAsTable(f"{CATALOG_SCHEMA}.cows")

    studies = [study_row(row) for row in conn.execute("SELECT * FROM Studies")]
    append(studies, STUDY_SCHEMA, "studies")
    study_animals = [
        dict(row)
        for row in conn.execute(
            "SELECT study_id, animal_id, study_group FROM StudyAnimals"
        )
    ]
    append(study_animals, STUDY_ANIMAL_SCHEMA, "study_animals")

    n_events = 0
    cur = conn.execute(
        "SELECT event_id, animal_id, event_type, datetime, metadata, study_id"
        " FROM AnimalEvents"
    )
    while True:
        batch = cur.fetchmany(BATCH_SIZE)
        if not batch:
            break
        rows = [dict(row) for row in batch]
        df = spark.createDataFrame(rows, schema=EVENT_SCHEMA)
        df = df.withColumn("datetime", to_timestamp("datetime")).withColumn(
            "metadata", expr("parse_json(metadata)")
        )
        df.write.format("delta").mode("append").saveAsTable(
            f"{CATALOG_SCHEMA}.animal_events"
        )
        n_events += len(rows)

    conn.close()
    return len(herds), len(cows), n_events


# COMMAND ----------

total_herds = total_cows = total_events = 0
for i, db_path in enumerate(db_paths, 1):
    n_herds, n_cows, n_events = load_farm(db_path)
    total_herds += n_herds
    total_cows += n_cows
    total_events += n_events
    print(
        f"[{i}/{len(db_paths)}] {db_path.name}: {n_herds} herds, {n_cows} cows, {n_events:,} events"
    )

print(
    f"finished: {total_herds} herds, {total_cows} cows, {total_events:,} events across {len(db_paths)} farms"
)
