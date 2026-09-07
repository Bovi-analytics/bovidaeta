"""Entry point for `python -m bovidaeta.simulation`."""

from .main import Farm, SimConfig

if __name__ == "__main__":
    farm = Farm(SimConfig())
    if not farm.sim_cancelled:
        farm.run_simulation()
