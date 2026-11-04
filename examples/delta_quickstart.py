# Databricks notebook source
# MAGIC %md
# MAGIC # Working with farm events in Databricks (Delta)
# MAGIC
# MAGIC `DairyData.from_delta` reads the multi-farm tables in Unity Catalog.
# MAGIC Import this file into Databricks.
# MAGIC
# MAGIC If you're NOT using the Bovi-Analytics Databricks workspace,
# MAGIC before running this notebook, ensure that:
# MAGIC - Delta tables exist: `bovidaeta/schemas/delta.sql`
# MAGIC - Ensure there's a Volume with one or more SQLite databases, one per farm
# MAGIC - Delta tables are filled: `pipelines/sqlite_to_delta.py`
# MAGIC - You build the package wheel and upload it your workspace
# MAGIC - Change the `CATALOG_LOCATION` below

# COMMAND ----------

# MAGIC %pip install /Volumes/cornell_catalog/cornell_schema/libs/bovidaeta-0.1.1-py3-none-any.whl
# MAGIC %restart_python

# COMMAND ----------

CATALOG_LOCATION = "cornell_catalog.cornell_schema"
dbutils.widgets.text("catalog_schema", CATALOG_LOCATION)
CATALOG_SCHEMA = dbutils.widgets.get("catalog_schema")

# COMMAND ----------

from datetime import UTC, datetime

from pyspark.sql import functions as F

from bovidaeta import DairyData, EventType, to_polars

data = DairyData.from_delta(CATALOG_SCHEMA)
print(data)

# COMMAND ----------

# MAGIC %md ## 1. Simple counts

# COMMAND ----------

print(f"herds:    {data.load_herds().count():,}")
print(f"cow rows: {data.load_cows().count():,}")
print(f"events:   {data.load_events().count():,}")

data.load_events().groupBy("event_type").count().orderBy(F.desc("count")).show(
    truncate=False
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Filtering
# MAGIC
# MAGIC `events` is partitioned by `(event_type, event_year)`. Meaning that
# MAGIC passing`subset_events` together with a datetime range lets Delta skip
# MAGIC huge amounts of data. This saves a lot of time and memory!

# COMMAND ----------

milk = data.load_events(
    dts_start=datetime(2019, 1, 1, tzinfo=UTC),
    dts_end=datetime(2021, 1, 1, tzinfo=UTC),
    subset_events=[EventType.MILK_RECORDING],
    subset_metadata={"milking_yield": "DOUBLE"},
)
milk.show(5, truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Casting metadata
# MAGIC
# MAGIC Metadata is stored as `VARIANT` here, which will not aggregate until
# MAGIC it is cast, hence the `{"milking_yield": "DOUBLE"}` mapping above.
# MAGIC Passing a plain list of keys projects the raw variant instead, which
# MAGIC is what you want when you only mean to look at it.

# COMMAND ----------

data.load_events(subset_events=[EventType.DIAGNOSIS], subset_metadata=["disease"]).show(
    5, truncate=False
)

# COMMAND ----------

# MAGIC %md
# MAGIC ### Narrowing to cows and herds

# COMMAND ----------

one_herd = data.load_herds().select("herd_id").limit(1).collect()[0]["herd_id"]
print(f"herd {one_herd}: {data.load_events(subset_herds=[one_herd]).count():,} events")

some_cow = (
    data.load_cows(subset_herds=[one_herd]).select("animal_id").limit(1).collect()[0][0]
)
data.load_events(subset_cows=[some_cow]).groupBy("event_type").count().show(
    truncate=False
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Nested metadata
# MAGIC
# MAGIC Only top-level keys can be projected.
# MAGIC `DiagnosisMetadata` nests, so ask for `disease` and reach into it
# MAGIC afterwards.

# COMMAND ----------

diag = data.load_events(
    subset_events=[EventType.DIAGNOSIS],
    subset_metadata=["disease"],
).withColumn("disease_code", F.expr("disease:disease_code::STRING"))

diag.groupBy("disease_code").count().orderBy(F.desc("count")).show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Example question: does mastitis cost milk?
# MAGIC
# MAGIC This is just to show how to work with the bovidaeta through Spark, it's not a
# MAGIC proper scientific analysis, so take the results with a big grain of salt!

# COMMAND ----------

per_cow = milk.groupBy("animal_id").agg(F.avg("milking_yield").alias("avg_yield"))
mastitis = diag.filter(F.col("disease_code") == "MAS").select("animal_id").distinct()

comparison = (
    per_cow.join(
        mastitis.withColumn("has_mastitis", F.lit(True)), on="animal_id", how="left"
    )
    .withColumn(
        "group", F.when(F.col("has_mastitis"), "mastitis").otherwise("no_mastitis")
    )
    .groupBy("group")
    .agg(F.count("*").alias("n_cows"), F.avg("avg_yield").alias("avg_yield"))
)
comparison.show(truncate=False)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Optional: Crossing back to polars
# MAGIC
# MAGIC `to_polars` collects to the driver, so aggregate first.
# MAGIC Using `to_polars` is only relevant if you want to reuse polars-shaped code.

# COMMAND ----------

print(to_polars(comparison))
