"""Loading dairy farm data.

`DairyData` is the only class you need: `DairyData.from_sqlite(...)` for a
farm's local database, `DairyData.from_delta(...)` for the multi-farm
tables in Unity Catalog. See `README.md` for the contract they share and
the places the two stores genuinely differ.

The Delta backend is imported lazily, so a farm device never needs pyspark
installed.
"""

from typing import TYPE_CHECKING, Any

from .dairy_data import DairyData

if TYPE_CHECKING:  # pragma: no cover
    from .delta import to_polars

__all__ = ["DairyData", "to_polars"]


def __getattr__(name: str) -> Any:
    if name == "to_polars":
        from .delta import to_polars

        return to_polars
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
