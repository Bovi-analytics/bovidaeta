"""Smoke test run by CI on every supported Python version.

Simulates a tiny farm and reads it back through the public API, so a broken
import, schema or loader fails CI even without a test suite.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import bovidaeta
from bovidaeta import DairyData, EventType, load_lactations

print(f"bovidaeta {bovidaeta.__version__} on Python {sys.version.split()[0]}")

with tempfile.TemporaryDirectory() as tmp:
    db = Path(tmp) / "farm.db"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "bovidaeta.simulation",
            "--animals",
            "40",
            "--years",
            "1",
            "--db",
            str(db),
            "--seed",
            "1",
            "--yes",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    data = DairyData.from_sqlite(db)
    events = data.load_events()
    cows = data.load_cows()
    herds = data.load_herds()
    milk = data.load_events(
        subset_events=[EventType.MILK_RECORDING], subset_metadata=["milking_yield"]
    )
    lactations = load_lactations(data)

    print(
        f"events={events.height} cows={cows.height} herds={herds.height} "
        f"milk_recordings={milk.height} lactations={lactations.height}"
    )
    assert events.height > 0 and cows.height > 0 and herds.height > 0
    assert milk.height > 0 and "milking_yield" in milk.columns
    assert lactations.height > 0
