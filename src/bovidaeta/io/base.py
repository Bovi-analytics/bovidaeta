"""The query contract shared by every `DairyData` backend.

`DairyData` is the one public loader. It validates its arguments here, then
hands them to a backend object - `_SQLiteBackend` for a farm's local
database, `_DeltaBackend` for the multi-farm tables in Unity Catalog -
which knows how to turn them into a query for its store.

Adding a third source means writing another `EventBackend` and one
`DairyData.from_*` classmethod. It does not mean another public class, and
it cannot change `load_events`'s signature, because there is only one.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from typing import Any

from ..enums import EventType

# Columns every backend returns, in this order, before any metadata columns.
# `study_id` is null for farm data.
BASE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "animal_id",
    "event_type",
    "datetime",
    "study_id",
)

# Columns of the studies and study-animals tables, in the order returned.
STUDY_COLUMNS: tuple[str, ...] = (
    "study_id",
    "project",
    "name",
    "description",
    "start_date",
    "end_date",
    "doi_or_protocol_url",
    "open_data",
    "license",
    "credit_required",
    "contributors",
)
STUDY_ANIMAL_COLUMNS: tuple[str, ...] = ("study_id", "animal_id", "study_group")

# Characters allowed in a metadata key we are willing to interpolate into a
# query. Keys come from the caller, and neither SQLite's `json_extract`
# paths nor Delta's `metadata:key` syntax can be parameterised, so they are
# validated rather than bound.
_SAFE_KEY = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")

# Cast targets accepted in a `subset_metadata` mapping, spelled in Delta's
# SQL types and translated per backend. Restricted to a known set because,
# like the keys, these are interpolated rather than bound.
CAST_TYPES: dict[str, str] = {
    "STRING": "TEXT",
    "BOOLEAN": "INTEGER",
    "INT": "INTEGER",
    "BIGINT": "INTEGER",
    "FLOAT": "REAL",
    "DOUBLE": "REAL",
    "DECIMAL": "REAL",
    "DATE": "TEXT",
    "TIMESTAMP": "TEXT",
}


def normalise_event_types(
    subset_events: Iterable[EventType | str] | None,
) -> list[str] | None:
    """Accept `EventType` members, plain strings, or a mix; return wire values."""
    if not subset_events:
        return None
    return [e.value if isinstance(e, EventType) else str(e) for e in subset_events]


def normalise_ids(subset: Iterable[str] | None) -> list[str] | None:
    """Accept any iterable of id strings (including UUIDs); return a list of str.

    Iterated rather than tested for truth, so a polars `Series` (say the
    `animal_id` column of `load_study_animals`) can be passed as it is.
    """
    if subset is None:
        return None
    return [str(s) for s in subset] or None


def normalise_farm_numbers(subset: Iterable[int | str] | None) -> list[int] | None:
    """Accept farm numbers as ints or numeric strings (" 33119"); return a list of int."""
    if not subset:
        return None
    numbers = []
    for s in subset:
        try:
            numbers.append(int(str(s).strip()))
        except ValueError:
            raise ValueError(
                f"Farm number must be a whole number, got {s!r}."
            ) from None
    return numbers


def normalise_metadata(
    subset_metadata: Iterable[str] | Mapping[str, str] | None,
) -> dict[str, str | None] | None:
    """Return `{key: cast_or_None}`, rejecting anything not a bare identifier.

    Only top-level keys can be requested. Nested metadata (for example
    `DiagnosisMetadata.disease`, stored as `{"disease": {"disease_code":
    ...}}`) is requested by its top-level key and unnested afterwards.
    """
    if not subset_metadata:
        return None

    if isinstance(subset_metadata, Mapping):
        pairs = [(str(k), str(v).upper().strip()) for k, v in subset_metadata.items()]
    else:
        pairs = [(str(k), None) for k in subset_metadata]

    out: dict[str, str | None] = {}
    for key, cast in pairs:
        if not key or set(key) - _SAFE_KEY:
            raise ValueError(
                f"{key!r} is not a usable metadata key. Keys must be bare "
                "identifiers (letters, digits, underscore). Nested metadata is "
                "requested by its top-level key and unnested after loading."
            )
        if cast is not None and cast not in CAST_TYPES:
            raise ValueError(
                f"{cast!r} is not an allowed cast for metadata key {key!r}. "
                f"Use one of: {', '.join(sorted(CAST_TYPES))}."
            )
        out[key] = cast
    return out


def validate_datetime_range(
    dts_start: datetime | None, dts_end: datetime | None
) -> tuple[datetime | None, datetime | None]:
    """Reject an inverted range up front, rather than silently returning nothing."""
    if dts_start and dts_end and dts_start > dts_end:
        raise ValueError(f"dts_start ({dts_start}) is after dts_end ({dts_end})")
    return dts_start, dts_end


def validate_identifier(name: str, what: str) -> str:
    """Check a dotted SQL identifier that will be interpolated into a query."""
    for part in name.split("."):
        if not part or not part.replace("_", "").isalnum():
            raise ValueError(f"{name!r} is not a valid {what}")
    return name


def resolved_columns(
    subset_metadata: Sequence[str] | Mapping[str, Any] | None,
) -> tuple[str, ...]:
    """The column names a `load_events` call with these arguments will return."""
    if subset_metadata:
        return BASE_COLUMNS + tuple(subset_metadata)
    return BASE_COLUMNS + ("metadata",)


class EventBackend(ABC):
    """One storage backend behind `DairyData`.

    Receives arguments already normalised and validated by `DairyData`, so
    an implementation only has to build and run its own query. Each method
    returns whatever frame is native to that store.
    """

    #: Short name used in `DairyData.backend` and `repr`.
    name: str

    @abstractmethod
    def load_events(
        self,
        dts_start: datetime | None,
        dts_end: datetime | None,
        event_types: list[str] | None,
        metadata: dict[str, str | None] | None,
        cow_ids: list[str] | None,
        herd_ids: list[str] | None,
        study_ids: list[str] | None,
    ) -> Any: ...

    @abstractmethod
    def load_cows(
        self,
        cow_ids: list[str] | None,
        herd_ids: list[str] | None,
        farm_numbers: list[int] | None,
    ) -> Any: ...

    @abstractmethod
    def load_herds(self, herd_ids: list[str] | None) -> Any: ...

    @abstractmethod
    def load_studies(self, study_ids: list[str] | None) -> Any: ...

    @abstractmethod
    def load_study_animals(self, study_ids: list[str] | None) -> Any: ...
