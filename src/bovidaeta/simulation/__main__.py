"""Entry point for `python -m bovidaeta.simulation`.

    python -m bovidaeta.simulation                      # 200 animals, 10 years, ~/nsf-data/dairy_farm.db
    python -m bovidaeta.simulation --animals 800 --years 3 --db ~/data/dairy_farm.db --yes
"""

import argparse
import random
from datetime import date
from pathlib import Path

from .main import DB_PATH, Farm, SimConfig


def main() -> None:
    p = argparse.ArgumentParser(prog="python -m bovidaeta.simulation", description=__doc__.splitlines()[0])
    p.add_argument("--animals", type=int, default=SimConfig().target_herd_size,
                   help="target number of animals on the farm, young stock included (about half are cows)")
    p.add_argument("--years", type=float, default=SimConfig().sim_years, help="years of history to simulate")
    p.add_argument("--end-date", type=date.fromisoformat, default=None, help="last simulated day (default: today)")
    p.add_argument("--db", type=Path, default=DB_PATH, help=f"output database (default: {DB_PATH})")
    p.add_argument("--seed", type=int, default=None, help="random seed, for a reproducible farm")
    p.add_argument("--yes", action="store_true", help="overwrite an existing database without asking")
    a = p.parse_args()
    if a.seed is not None:
        random.seed(a.seed)
    conf = SimConfig(target_herd_size=a.animals, sim_years=a.years, sim_end_date=a.end_date)
    farm = Farm(conf, db_path=a.db.expanduser(), overwrite=True if a.yes else None)
    if not farm.sim_cancelled:
        farm.run_simulation()


if __name__ == "__main__":
    main()
