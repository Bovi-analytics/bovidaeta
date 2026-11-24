"""Studies: models, both loader backends, and migrating an existing database.

The Delta half runs against a local Spark session, with the tables created
from the real `delta.sql` and migration, rewritten to parquet (no Delta jars
or Unity Catalog needed). It is skipped when pyspark is not installed.
"""

import json
import re
import sqlite3
from datetime import date, datetime, timezone

import polars as pl
import pytest
from pydantic import ValidationError

from bovidaeta import DairyData, Event, EventType, Study, StudyAnimal
from bovidaeta.io.base import BASE_COLUMNS, STUDY_ANIMAL_COLUMNS, STUDY_COLUMNS
from bovidaeta.schemas import (
    DELTA_SCHEMA,
    DELTA_STUDIES_MIGRATION,
    SQLITE_SCHEMA,
    SQLITE_STUDIES_MIGRATION,
    read_schema,
)

HERD = "h-1"
S1 = "11111111-1111-1111-1111-111111111111"
S2 = "22222222-2222-2222-2222-222222222222"
COWS = ["cow-a", "cow-b", "cow-c"]

STUDIES = [
    # study_id, project, name, description, start, end, doi, open_data, license, credit, contributors
    (
        S1,
        "GEMS",
        "Heat stress",
        "Cooling trial",
        "2024-01-01",
        "2024-06-30",
        "https://doi.org/10.0/x",
        1,
        "CC-BY-4.0",
        0,
        "A. Researcher",
    ),
    (S2, "GEMS", "Fat supplement", None, "2024-03-01", None, None, 0, None, 1, None),
]

# cow-a is in both studies.
STUDY_ANIMALS = [
    (S1, "cow-a", "control"),
    (S1, "cow-b", "treatment"),
    (S2, "cow-a", "high_fat"),
    (S2, "cow-c", None),
]

# event_id, datetime, event_type, animal_id, metadata, study_id
EVENTS = [
    ("e1", "2024-01-01 06:00:00", "Calving", "cow-a", {}, None),
    (
        "e2",
        "2024-02-01 06:00:00",
        "MilkRecording",
        "cow-a",
        {"milking_yield": 30.0},
        S1,
    ),
    (
        "e3",
        "2024-02-01 07:00:00",
        "MilkRecording",
        "cow-b",
        {"milking_yield": 25.0},
        S1,
    ),
    (
        "e4",
        "2024-04-01 06:00:00",
        "MilkRecording",
        "cow-a",
        {"milking_yield": 32.0},
        S2,
    ),
    (
        "e5",
        "2024-04-01 07:00:00",
        "MilkRecording",
        "cow-c",
        {"milking_yield": 28.0},
        S2,
    ),
    ("e6", "2024-05-01 06:00:00", "Calving", "cow-c", {}, None),
]
FARM_EVENTS = {"e1", "e6"}

# sqlite.sql as it was before studies, to check the migration against.
SQLITE_SCHEMA_BEFORE_STUDIES = """
CREATE TABLE Herds (herd_id TEXT PRIMARY KEY, source_id INTEGER NOT NULL, country_code TEXT);
CREATE TABLE AnimalEvents (
    event_id   TEXT PRIMARY KEY,
    datetime   TEXT NOT NULL,
    event_type TEXT NOT NULL,
    animal_id  TEXT NOT NULL,
    metadata   TEXT NOT NULL
);
CREATE TABLE Cows (animal_id TEXT PRIMARY KEY, herd_id TEXT NOT NULL, sire_ear_tag TEXT, metadata TEXT NOT NULL);
CREATE INDEX idx_events_type_dts   ON AnimalEvents (event_type, datetime);
CREATE INDEX idx_events_animal_dts ON AnimalEvents (animal_id, datetime);
"""


def _event_rows(with_study: bool) -> list[tuple]:
    rows = []
    for event_id, dts, event_type, animal_id, metadata, study_id in EVENTS:
        row = (event_id, dts, event_type, animal_id, json.dumps(metadata))
        rows.append(row + (study_id,) if with_study else row)
    return rows


def _fill_farm(conn: sqlite3.Connection, with_study: bool) -> None:
    conn.execute(
        "INSERT INTO Herds (herd_id, source_id, country_code) VALUES (?, 1, 'US')",
        (HERD,),
    )
    conn.executemany(
        "INSERT INTO Cows (animal_id, herd_id, sire_ear_tag, metadata) VALUES (?, ?, NULL, '{}')",
        [(cow, HERD) for cow in COWS],
    )
    cols = "event_id, datetime, event_type, animal_id, metadata"
    if with_study:
        conn.executemany(
            f"INSERT INTO AnimalEvents ({cols}, study_id) VALUES (?, ?, ?, ?, ?, ?)",
            _event_rows(with_study=True),
        )
    else:
        conn.executemany(
            f"INSERT INTO AnimalEvents ({cols}) VALUES (?, ?, ?, ?, ?)",
            _event_rows(with_study=False),
        )


@pytest.fixture
def sqlite_db(tmp_path):
    db = tmp_path / "gems.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(read_schema(SQLITE_SCHEMA))
        _fill_farm(conn, with_study=True)
        conn.executemany(f"INSERT INTO Studies VALUES ({', '.join('?' * 11)})", STUDIES)
        conn.executemany("INSERT INTO StudyAnimals VALUES (?, ?, ?)", STUDY_ANIMALS)
    conn.close()
    return db


# --- Spark ------------------------------------------------------------------


def _spark_statements(sql: str) -> list[str]:
    """Rewrite Databricks DDL so it runs on plain local Spark.

    Delta and Unity Catalog features become their plain-Spark equivalents:
    parquet instead of Delta, no primary keys or generated columns, no
    `USE CATALOG` (the caller picks the database). Views are skipped.
    """
    text = "\n".join(line.split("--")[0] for line in sql.splitlines())
    out = []
    for stmt in text.split(";"):
        stmt = stmt.strip()
        if not stmt or re.match(r"(USE|CREATE SCHEMA|CREATE OR REPLACE VIEW)\b", stmt):
            continue
        stmt = re.sub(r",\s*CONSTRAINT [^\n]*", "", stmt)
        stmt = re.sub(r"GENERATED ALWAYS AS \(YEAR\(datetime\)\)", "", stmt)
        stmt = stmt.replace("USING DELTA", "USING PARQUET")
        out.append(stmt)
    return out


@pytest.fixture(scope="module")
def spark(tmp_path_factory):
    pytest.importorskip("pyspark")
    from pyspark.sql import SparkSession

    session = (
        SparkSession.builder.master("local[1]")
        .appName("bovidaeta-tests")
        .config("spark.sql.warehouse.dir", str(tmp_path_factory.mktemp("warehouse")))
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


def _spark_db(spark, name: str, ddl: list[str]) -> str:
    spark.sql(f"DROP DATABASE IF EXISTS {name} CASCADE")
    spark.sql(f"CREATE DATABASE {name}")
    spark.catalog.setCurrentDatabase(name)
    for stmt in ddl:
        spark.sql(stmt)
    return f"spark_catalog.{name}"


def _spark_fill(spark, schema: str, with_study: bool) -> None:
    spark.sql(
        f"INSERT INTO {schema}.herds (herd_id, source_id, country_code) VALUES ('{HERD}', 1, 'US')"
    )
    spark.createDataFrame(
        [(c, HERD) for c in COWS], "animal_id STRING, herd_id STRING"
    ).createOrReplaceTempView("new_cows")
    spark.sql(f"INSERT INTO {schema}.cows (animal_id, herd_id) SELECT * FROM new_cows")
    spark.createDataFrame(
        _event_rows(with_study=True),
        "event_id STRING, datetime STRING, event_type STRING, animal_id STRING, metadata STRING, study_id STRING",
    ).createOrReplaceTempView("new_events")
    cols = "event_id, animal_id, event_type, datetime, event_year, metadata"
    select = (
        "event_id, animal_id, event_type, to_timestamp(datetime), "
        "year(to_timestamp(datetime)), parse_json(metadata)"
    )
    if with_study:
        cols += ", study_id"
        select += ", study_id"
    spark.sql(
        f"INSERT INTO {schema}.animal_events ({cols}) SELECT {select} FROM new_events"
    )


@pytest.fixture(scope="module")
def delta_schema(spark):
    schema = _spark_db(spark, "gems", _spark_statements(read_schema(DELTA_SCHEMA)))
    _spark_fill(spark, schema, with_study=True)
    spark.createDataFrame(
        [
            (
                s[0],
                s[1],
                s[2],
                s[3],
                date.fromisoformat(s[4]),
                s[5] and date.fromisoformat(s[5]),
                s[6],
                bool(s[7]),
                s[8],
                bool(s[9]),
                s[10],
            )
            for s in STUDIES
        ],
        "study_id STRING, project STRING, name STRING, description STRING, start_date DATE, "
        "end_date DATE, doi_or_protocol_url STRING, open_data BOOLEAN, license STRING, "
        "credit_required BOOLEAN, contributors STRING",
    ).createOrReplaceTempView("new_studies")
    spark.sql(f"INSERT INTO {schema}.studies SELECT * FROM new_studies")
    spark.createDataFrame(
        STUDY_ANIMALS, "study_id STRING, animal_id STRING, study_group STRING"
    ).createOrReplaceTempView("new_study_animals")
    spark.sql(f"INSERT INTO {schema}.study_animals SELECT * FROM new_study_animals")
    return schema


# --- both backends ----------------------------------------------------------


def _rows(df) -> list[dict]:
    if isinstance(df, pl.DataFrame):
        return df.to_dicts()
    return [row.asDict() for row in df.collect()]


def _ids(df, col: str = "event_id") -> set:
    return {row[col] for row in _rows(df)}


@pytest.fixture(params=["sqlite", "delta"])
def data(request) -> DairyData:
    if request.param == "sqlite":
        return DairyData.from_sqlite(request.getfixturevalue("sqlite_db"))
    schema = request.getfixturevalue("delta_schema")
    return DairyData.from_delta(schema, spark=request.getfixturevalue("spark"))


def test_events_have_study_id(data):
    df = data.load_events()
    assert tuple(df.columns) == BASE_COLUMNS + ("metadata",)
    by_event = {row["event_id"]: row["study_id"] for row in _rows(df)}
    assert by_event == {e[0]: e[5] for e in EVENTS}


def test_subset_studies(data):
    assert _ids(data.load_events(subset_studies=[S1])) == {"e2", "e3"}
    assert _ids(data.load_events(subset_studies=[S1, S2])) == {"e2", "e3", "e4", "e5"}
    assert _ids(data.load_events(subset_studies=["no-such-study"])) == set()


def test_subset_studies_combines_with_other_filters(data):
    # cow-a is in both studies; only its S2 event.
    assert _ids(data.load_events(subset_cows=["cow-a"], subset_studies=[S2])) == {"e4"}
    assert (
        _ids(
            data.load_events(subset_events=[EventType.CALVING], subset_studies=[S1, S2])
        )
        == set()
    )
    assert _ids(
        data.load_events(
            dts_start=datetime(2024, 3, 1, tzinfo=timezone.utc),
            subset_studies=[S1, S2],
        )
    ) == {"e4", "e5"}


def test_load_studies(data):
    studies = data.load_studies()
    assert tuple(studies.columns) == STUDY_COLUMNS
    by_id = {row["study_id"]: row for row in _rows(studies)}
    assert set(by_id) == {S1, S2}
    assert by_id[S1]["open_data"] is True and by_id[S1]["credit_required"] is False
    assert by_id[S2]["open_data"] is False and by_id[S2]["credit_required"] is True
    assert by_id[S2]["end_date"] is None
    assert str(by_id[S1]["start_date"]) == "2024-01-01"

    assert _ids(data.load_studies(subset_studies=[S2]), "study_id") == {S2}


def test_cow_in_two_studies(data):
    animals = data.load_study_animals()
    assert tuple(animals.columns) == STUDY_ANIMAL_COLUMNS
    pairs = {(r["study_id"], r["animal_id"]): r["study_group"] for r in _rows(animals)}
    assert pairs == {(s, a): g for s, a, g in STUDY_ANIMALS}

    s2 = _rows(data.load_study_animals(subset_studies=[S2]))
    assert {r["animal_id"] for r in s2} == {"cow-a", "cow-c"}

    # A study's animals, passed on as subset_cows, give their full history:
    # cow-a's farm calving and its S2 milking included.
    s1_animals = [
        r["animal_id"] for r in _rows(data.load_study_animals(subset_studies=[S1]))
    ]
    assert _ids(data.load_events(subset_cows=s1_animals)) == {"e1", "e2", "e3", "e4"}


def test_subset_studies_with_metadata(data):
    df = data.load_events(
        subset_studies=[S1], subset_metadata={"milking_yield": "DOUBLE"}
    )
    assert tuple(df.columns) == BASE_COLUMNS + ("milking_yield",)
    assert {r["event_id"]: r["milking_yield"] for r in _rows(df)} == {
        "e2": 30.0,
        "e3": 25.0,
    }


# --- migrating an existing database -----------------------------------------


def test_sqlite_migration(tmp_path, sqlite_db):
    db = tmp_path / "old_farm.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(SQLITE_SCHEMA_BEFORE_STUDIES)
        _fill_farm(conn, with_study=False)
    conn.close()

    conn = sqlite3.connect(db)
    conn.executescript(read_schema(SQLITE_STUDIES_MIGRATION))
    # A second run is refused and changes nothing.
    with pytest.raises(sqlite3.OperationalError, match="duplicate column"):
        conn.executescript(read_schema(SQLITE_STUDIES_MIGRATION))
    conn.rollback()

    # Same tables and columns, in the same order, as a new database.
    def layout(c):
        tables = [
            r[0]
            for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        return {
            t: [r[1:] for r in c.execute(f"PRAGMA table_info({t})")] for t in tables
        }

    with sqlite3.connect(sqlite_db) as fresh:
        assert layout(conn) == layout(fresh)
    conn.close()

    data = DairyData.from_sqlite(db)
    events = data.load_events().sort("event_id")
    expected = pl.DataFrame(
        [r + (None,) for r in _event_rows(with_study=False)],
        schema={
            c: pl.String
            for c in (
                "event_id",
                "datetime",
                "event_type",
                "animal_id",
                "metadata",
                "study_id",
            )
        },
        orient="row",
    ).select(*BASE_COLUMNS, "metadata")
    assert events.equals(expected)
    assert events["study_id"].null_count() == len(EVENTS)
    assert data.load_studies().height == 0
    assert data.load_study_animals().height == 0
    assert data.load_events(subset_studies=[S1]).height == 0


def test_delta_migration(spark, delta_schema):
    new_tables = {"studies", "study_animals"}
    # delta.sql without what migration 0001 adds = the tables as they were.
    before = [
        re.sub(r",\s*study_id\s+STRING\b", "", stmt)
        for stmt in _spark_statements(read_schema(DELTA_SCHEMA))
        if not any(f"TABLE IF NOT EXISTS {t} " in stmt for t in new_tables)
    ]
    schema = _spark_db(spark, "old_farms", before)
    _spark_fill(spark, schema, with_study=False)
    assert "study_id" not in spark.table(f"{schema}.animal_events").columns
    tables = {t.name for t in spark.catalog.listTables("old_farms")}
    assert not tables & new_tables

    for stmt in _spark_statements(read_schema(DELTA_STUDIES_MIGRATION)):
        spark.sql(stmt)

    # Same columns, in the same order, as tables made with the current delta.sql.
    for table in ("herds", "cows", "animal_events", *new_tables):
        assert (
            spark.table(f"{schema}.{table}").columns
            == spark.table(f"{delta_schema}.{table}").columns
        )

    data = DairyData.from_delta(schema, spark=spark)
    events = sorted(_rows(data.load_events()), key=lambda r: r["event_id"])
    assert [(r["event_id"], r["animal_id"], r["event_type"]) for r in events] == [
        (e[0], e[3], e[2]) for e in EVENTS
    ]
    assert all(r["study_id"] is None for r in events)
    assert data.load_studies().count() == 0
    assert data.load_study_animals().count() == 0


# --- models -----------------------------------------------------------------


def test_models():
    study = Study(study_id=S1, project="GEMS", start_date=date(2024, 1, 1))
    assert study.open_data is False and study.credit_required is None
    with pytest.raises(ValidationError, match="before start_date"):
        Study(study_id=S1, start_date=date(2024, 2, 1), end_date=date(2024, 1, 1))

    member = StudyAnimal(
        study_id=S1,
        animal_id="33333333-3333-3333-3333-333333333333",
        study_group="control",
    )
    assert str(member.study_id) == S1

    event = Event(
        event_type=EventType.CALVING,
        animal_id_source="1234",
        datetime=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    assert event.study_id is None
    assert str(event.model_copy(update={"study_id": S2}).study_id) == S2


def test_study_animals_series_as_subset_cows(sqlite_db):
    # The documented pattern: a polars column passed straight on.
    data = DairyData.from_sqlite(sqlite_db)
    animals = data.load_study_animals(subset_studies=[S2])
    assert _ids(data.load_events(subset_cows=animals["animal_id"])) == {
        "e1",
        "e2",
        "e4",
        "e5",
        "e6",
    }
