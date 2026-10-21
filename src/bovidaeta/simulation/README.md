# Data simulation

`main.py` produces events for cows on a dairy farm and writes them to a
SQLite database in the format described by
[`../schemas/sqlite.sql`](../schemas/sqlite.sql).

```bash
python -m bovidaeta.simulation                     # 200 animals, 10 years, ~/nsf-data/dairy_farm.db
python -m bovidaeta.simulation --animals 800 --years 3 --db ~/data/dairy_farm.db --yes --seed 7
```

`--animals` counts every animal on the farm, young stock included; about half
of them are cows. More parameters are tunable via `SimConfig`.

Cows get short pronounceable ear tags such as `BOKA` or `MIRU` (stored in the
`sire_ear_tag` column, which is what the tools look a cow up by; lookups are
case-insensitive), so they are easy to remember and type in a demo. The tool's purpose is to make
dummy data easy to come by, so you can:

- Try out working with the library (see
  [`examples/sqlite_quickstart.py`](../../../examples/sqlite_quickstart.py))
- Stress test systems using the library
- Produce input for the SQLite → Delta pipeline

Although it aims to create biologically plausible data, that is not the
main purpose: the simulation is heavily simplified. It is also not
optimised for performance and can take a few minutes with the default
settings.
