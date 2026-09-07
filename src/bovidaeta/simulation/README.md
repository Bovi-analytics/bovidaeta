# Data simulation

`main.py` produces events for cows on a dairy farm and writes them to a
SQLite database in the format described by
[`../schemas/sqlite.sql`](../schemas/sqlite.sql).

```bash
python -m bovidaeta.simulation
```

Various parameters are tunable via `SimConfig`, including the number of
cows and the number of simulated years. The tool's purpose is to make
dummy data easy to come by, so you can:

- Try out working with the library (see
  [`examples/sqlite_quickstart.py`](../../../examples/sqlite_quickstart.py))
- Stress test systems using the library
- Produce input for the SQLite → Delta pipeline

Although it aims to create biologically plausible data, that is not the
main purpose: the simulation is heavily simplified. It is also not
optimised for performance and can take a few minutes with the default
settings.
