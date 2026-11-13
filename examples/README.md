# Examples

Runnable walkthroughs of the two `DairyData` backends. Both ask the same
question (does a mastitis diagnosis cost milk yield?) so they can be read
side by side — and so the places they have to diverge are visible.

- **`sqlite_quickstart.py`** — `DairyData.from_sqlite`: one farm, a local
  `.db` file, polars. Run with `python examples/sqlite_quickstart.py`, or
  open as a notebook. Written against a real farm export; the simulator
  (`python -m bovidaeta.simulation`) produces the same format but does not
  yet emit every event type the example uses.
- **`delta_quickstart.py`** — `DairyData.from_delta`: every farm, Unity
  Catalog, Spark. Import into Databricks as a notebook (it carries the
  `# Databricks notebook source` header); it installs `bovidaeta` from PyPI.

Both are percent/notebook-format `.py` rather than `.ipynb`, so they diff
and review as source and run without a Jupyter install on a farm device.

The conceptual overview — which loader when, and where the two genuinely
differ — is in [`src/bovidaeta/io/README.md`](../src/bovidaeta/io/README.md).
